from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from nexora.threading import TaskPriority, TaskScheduler
from nexora.ecs.system import System


class ECSDependencyError(RuntimeError):
    """Base error for ECS system dependency problems."""


class ECSDependencyCycleError(ECSDependencyError):
    """Raised when the ECS system dependency graph contains a cycle."""


@dataclass(slots=True)
class SystemAccess:
    reads: frozenset[type]
    writes: frozenset[type]
    main_thread_only: bool
    priority: int
    depends_on: tuple[System, ...]


@dataclass(slots=True, eq=False)
class _SystemEntry:
    system: System
    access: SystemAccess
    registration_index: int


class ECSSystemScheduler:
    """
    Schedules ECS systems according to component access and dependencies.

    Systems inside the same batch are independent and can execute in
    parallel on the dedicated ECS system worker pool.

    The normal TaskScheduler remains available to ECS systems for
    parallel_query() and other background work.
    """

    def __init__(
        self,
        world,
        task_scheduler: TaskScheduler | None = None,
        *,
        system_workers: int | None = None,
    ):
        self.world = world

        # Normal game/ECS task scheduler.
        self.task_scheduler = task_scheduler

        # Dedicated pool for ECS systems.
        if system_workers is None:
            cpu_count = os.cpu_count() or 1
            system_workers = max(1, min(cpu_count - 1, 8))

        if system_workers < 1:
            raise ValueError("system_workers must be at least 1.")

        self.system_workers = system_workers

        self._system_executor = TaskScheduler(
            workers=system_workers
        )

        self._entries: list[_SystemEntry] = []
        self._batches: list[list[_SystemEntry]] = []

        self._dirty = True
        self._registration_counter = 0
        self._shutdown = False

    # ------------------------------------------------------------------
    # System registration
    # ------------------------------------------------------------------

    def add_system(
        self,
        system: System,
        *,
        reads: Iterable[type] = (),
        writes: Iterable[type] = (),
        priority: int = 0,
        main_thread_only: bool = False,
        depends_on: Iterable[System] = (),
    ) -> System:
        if self._shutdown:
            raise RuntimeError(
                "ECSSystemScheduler has already been shut down."
            )

        if not isinstance(system, System):
            raise TypeError(
                "system must be an instance of System."
            )

        if any(entry.system is system for entry in self._entries):
            raise ValueError(
                "System is already registered."
            )

        reads_set = frozenset(reads)
        writes_set = frozenset(writes)
        dependencies = tuple(depends_on)

        unknown_dependencies = [
            dependency
            for dependency in dependencies
            if not any(
                entry.system is dependency
                for entry in self._entries
            )
        ]

        if unknown_dependencies:
            raise ECSDependencyError(
                "System depends on an unregistered system."
            )

        access = SystemAccess(
            reads=reads_set,
            writes=writes_set,
            main_thread_only=main_thread_only,
            priority=priority,
            depends_on=dependencies,
        )

        entry = _SystemEntry(
            system=system,
            access=access,
            registration_index=self._registration_counter,
        )

        self._registration_counter += 1
        self._entries.append(entry)
        self._dirty = True

        system.initialize(self.world)

        return system

    def remove_system(self, system: System) -> None:
        for index, entry in enumerate(self._entries):
            if entry.system is system:
                system.shutdown(self.world)
                self._entries.pop(index)
                self._dirty = True
                return

    # ------------------------------------------------------------------
    # Dependency graph
    # ------------------------------------------------------------------

    @staticmethod
    def _access_conflict(
        first: SystemAccess,
        second: SystemAccess,
    ) -> bool:
        """
        Return True when two systems must not execute concurrently.
        """

        # Main-thread systems can never share a parallel batch.
        if first.main_thread_only or second.main_thread_only:
            return True

        # Writer -> reader conflict.
        if first.writes & second.reads:
            return True

        # Reader -> writer conflict.
        if second.writes & first.reads:
            return True

        # Writer -> writer conflict.
        if first.writes & second.writes:
            return True

        return False

    def _build_graph(self) -> dict[_SystemEntry, set[_SystemEntry]]:
        """
        Build directed dependency graph.

        graph[A] contains every system that must execute AFTER A.

        Example:

            A -> B

        means:

            A must finish before B starts.
        """

        graph: dict[_SystemEntry, set[_SystemEntry]] = {
            entry: set()
            for entry in self._entries
        }

        # --------------------------------------------------------------
        # Explicit dependencies
        # --------------------------------------------------------------

        for entry in self._entries:
            for dependency in entry.access.depends_on:
                dependency_entry = next(
                    candidate
                    for candidate in self._entries
                    if candidate.system is dependency
                )

                graph[dependency_entry].add(entry)

        # --------------------------------------------------------------
        # Automatic component access dependencies
        # --------------------------------------------------------------

        for index, first in enumerate(self._entries):
            for second in self._entries[index + 1:]:

                if not self._access_conflict(
                    first.access,
                    second.access,
                ):
                    continue

                # ------------------------------------------------------
                # Explicit dependency already establishes a direction.
                # ------------------------------------------------------

                if second.system in first.access.depends_on:
                    # second -> first
                    graph[second].add(first)
                    continue

                if first.system in second.access.depends_on:
                    # first -> second
                    graph[first].add(second)
                    continue

                # ------------------------------------------------------
                # No explicit dependency:
                # higher priority executes first.
                # ------------------------------------------------------

                if first.access.priority > second.access.priority:
                    graph[first].add(second)

                elif second.access.priority > first.access.priority:
                    graph[second].add(first)

                # ------------------------------------------------------
                # Same priority:
                # registration order wins.
                # ------------------------------------------------------

                elif (
                    first.registration_index
                    < second.registration_index
                ):
                    graph[first].add(second)

                else:
                    graph[second].add(first)

        return graph

    def _find_cycle(
        self,
        graph: dict[_SystemEntry, set[_SystemEntry]],
    ) -> list[_SystemEntry] | None:
        """
        Find a dependency cycle using DFS.

        Returns the cycle entries or None.
        """

        visiting: set[_SystemEntry] = set()
        visited: set[_SystemEntry] = set()
        path: list[_SystemEntry] = []

        def visit(entry: _SystemEntry):
            if entry in visiting:
                try:
                    index = path.index(entry)
                except ValueError:
                    index = 0

                return path[index:] + [entry]

            if entry in visited:
                return None

            visiting.add(entry)
            path.append(entry)

            for dependency in graph[entry]:
                cycle = visit(dependency)

                if cycle is not None:
                    return cycle

            path.pop()
            visiting.remove(entry)
            visited.add(entry)

            return None

        for entry in self._entries:
            cycle = visit(entry)

            if cycle is not None:
                return cycle

        return None

    def _rebuild(self) -> None:
        """
        Rebuild the execution batches.

        Uses Kahn's topological sorting algorithm.

        graph[A] -> systems after A

        Therefore:

            indegree[A] == number of systems that must
            execute before A.

        Systems with indegree 0 can execute immediately.
        """

        graph = self._build_graph()

        # --------------------------------------------------------------
        # Detect dependency cycles before creating batches.
        # --------------------------------------------------------------

        cycle = self._find_cycle(graph)

        if cycle is not None:
            names = " -> ".join(
                type(entry.system).__name__
                for entry in cycle
            )

            raise ECSDependencyCycleError(
                f"ECS system dependency cycle detected: {names}"
            )

        # --------------------------------------------------------------
        # Calculate indegree.
        #
        # graph[A] contains systems AFTER A.
        # Therefore every outgoing edge increases the target's
        # number of required predecessors.
        # --------------------------------------------------------------

        indegree: dict[_SystemEntry, int] = {
            entry: 0
            for entry in self._entries
        }

        for entry, following in graph.items():
            for other in following:
                indegree[other] += 1

        # --------------------------------------------------------------
        # Systems that have not yet been scheduled.
        # --------------------------------------------------------------

        remaining: set[_SystemEntry] = set(
            self._entries
        )

        batches: list[list[_SystemEntry]] = []

        # --------------------------------------------------------------
        # Build execution batches.
        # --------------------------------------------------------------

        while remaining:

            ready = [
                entry
                for entry in remaining
                if indegree[entry] == 0
            ]

            if not ready:
                # This should already have been caught by _find_cycle(),
                # but keep this as a safety net.
                raise ECSDependencyCycleError(
                    "ECS system dependency graph contains a cycle."
                )

            # Higher priority first.
            #
            # Registration order is used as deterministic tie-breaker.
            ready.sort(
                key=lambda entry: (
                    -entry.access.priority,
                    entry.registration_index,
                )
            )

            # Every ready system is independent from the perspective
            # of the dependency graph and can execute in this batch.
            batch = ready

            batches.append(batch)

            # ----------------------------------------------------------
            # Remove the current batch from the graph.
            # ----------------------------------------------------------

            for entry in batch:
                remaining.remove(entry)

            # ----------------------------------------------------------
            # Completing this batch removes one predecessor from all
            # systems that depend on it.
            # ----------------------------------------------------------

            for entry in batch:
                for following in graph[entry]:
                    indegree[following] -= 1

        self._batches = batches
        self._dirty = False

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute_system(
        self,
        entry: _SystemEntry,
        method_name: str,
        delta_time: float,
    ) -> None:
        system = entry.system
        method = getattr(system, method_name)

        # Every worker/main-thread system gets its own command buffer.
        self.world.create_command_buffer()

        try:
            method(
                self.world,
                delta_time,
            )
        finally:
            # No persistent system state is required here.
            # Systems access their command buffer through world.commands().
            pass

    def _execute(
        self,
        method_name: str,
        delta_time: float,
    ) -> None:
        if self._shutdown:
            raise RuntimeError(
                "ECSSystemScheduler has already been shut down."
            )

        if self._dirty:
            self._rebuild()

        for batch in self._batches:

            # ----------------------------------------------------------
            # Single-system batch
            # ----------------------------------------------------------

            if len(batch) == 1:
                entry = batch[0]

                if entry.access.main_thread_only:
                    self._execute_system(
                        entry,
                        method_name,
                        delta_time,
                    )

                else:
                    future = self._system_executor.submit(
                        self._execute_system,
                        entry,
                        method_name,
                        delta_time,
                        priority=TaskPriority.NORMAL,
                    )

                    # Wait for this system before moving to the next
                    # dependency batch.
                    future.result()

            # ----------------------------------------------------------
            # Parallel batch
            # ----------------------------------------------------------

            else:
                if any(
                    entry.access.main_thread_only
                    for entry in batch
                ):
                    raise ECSDependencyError(
                        "main_thread_only system found in parallel batch."
                    )

                futures = []

                for entry in batch:
                    futures.append(
                        self._system_executor.submit(
                            self._execute_system,
                            entry,
                            method_name,
                            delta_time,
                            priority=TaskPriority.NORMAL,
                        )
                    )

                # All systems in the batch must finish before:
                #
                # 1. commands are applied
                # 2. the next batch starts
                #
                self._system_executor.wait_all(futures)

            # ----------------------------------------------------------
            # ECS STRUCTURAL CHANGES
            # ----------------------------------------------------------

            # Important:
            #
            # Commands are applied AFTER the entire batch.
            #
            # This means:
            #
            # Batch 0:
            #   SpawnSystem
            #
            # -> apply commands
            #
            # Batch 1:
            #   DamageSystem
            #
            # -> apply commands
            #
            # Batch 2:
            #   DestroySystem
            #
            # -> apply commands
            #
            # Structural ECS changes therefore never occur while
            # systems are iterating over the archetypes.
            self.world.apply_commands()

    # ------------------------------------------------------------------
    # Public update methods
    # ------------------------------------------------------------------

    def update(
        self,
        delta_time: float,
    ) -> None:
        self._execute(
            "update",
            delta_time,
        )

    def fixed_update(
        self,
        fixed_delta_time: float,
    ) -> None:
        self._execute(
            "fixed_update",
            fixed_delta_time,
        )

    def render(
        self,
        interpolation: float,
    ) -> None:
        """
        Rendering always happens on the caller/main thread.

        SDL3 / GPU rendering must not be moved into worker threads.
        """

        if self._shutdown:
            return

        if self._dirty:
            self._rebuild()

        for batch in self._batches:
            for entry in batch:
                entry.system.render(
                    self.world,
                    interpolation,
                )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        if self._shutdown:
            return

        self._shutdown = True

        # Systems shut down in reverse registration order.
        for entry in reversed(self._entries):
            try:
                entry.system.shutdown(self.world)
            except Exception:
                pass

        self._entries.clear()
        self._batches.clear()

        self._system_executor.shutdown(
            wait=True
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def batches(self) -> list[list[System]]:
        if self._dirty:
            self._rebuild()

        return [
            [entry.system for entry in batch]
            for batch in self._batches
        ]

    def system_count(self) -> int:
        return len(self._entries)

    def batch_count(self) -> int:
        if self._dirty:
            self._rebuild()

        return len(self._batches)

    @property
    def executor(self) -> TaskScheduler:
        return self._system_executor

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown