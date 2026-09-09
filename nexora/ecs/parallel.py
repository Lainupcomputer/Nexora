from __future__ import annotations

from nexora.threading import TaskPriority, TaskScheduler


class ParallelChunkExecutor:
    """
    Executes chunk workloads in parallel using Nexora's worker pool.

    Chunks are distributed once per execution into balanced worker groups.
    """

    def __init__(
        self,
        scheduler: TaskScheduler,
        workers_per_batch: int | None = None,
    ):
        self.scheduler = scheduler

        if workers_per_batch is None:
            workers_per_batch = scheduler.worker_count

        if workers_per_batch < 1:
            raise ValueError(
                "workers_per_batch must be at least 1."
            )

        self.workers_per_batch = workers_per_batch

    def execute(
        self,
        chunks,
        function,
    ) -> None:

        chunk_count = len(chunks)

        if chunk_count == 0:
            return

        worker_count = min(
            self.workers_per_batch,
            chunk_count,
        )

        # Avoid creating more groups than necessary.
        groups = [
            []
            for _ in range(worker_count)
        ]

        # Balanced distribution.
        #
        # Instead of simply assigning chunks based on modulo,
        # distribute contiguous ranges. This improves cache
        # locality when archetypes contain many adjacent chunks.
        base_size = chunk_count // worker_count
        remainder = chunk_count % worker_count

        offset = 0

        futures = []

        for worker_index in range(worker_count):

            group_size = (
                base_size
                + (1 if worker_index < remainder else 0)
            )

            if group_size == 0:
                continue

            group = chunks[
                offset:
                offset + group_size
            ]

            offset += group_size

            futures.append(
                self.scheduler.submit(
                    function,
                    group,
                    priority=TaskPriority.NORMAL,
                )
            )

        self.scheduler.wait_all(futures)