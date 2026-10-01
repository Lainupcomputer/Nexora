from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from .bus import AudioBus
from .effects import LimiterEffect, audio_effect_from_state
from .send import AudioSend


class AudioMixer:
    """Owns the dynamic audio graph, routing, sends and mixer snapshots."""

    SNAPSHOT_VERSION = 1

    def __init__(self) -> None:
        self._buses: dict[str, AudioBus] = {}
        self._buses_by_id: dict[str, AudioBus] = {}
        self._sends: dict[str, AudioSend] = {}
        self._headroom_db = 0.0
        self._master_limiter: LimiterEffect | None = None

        self.add_bus(AudioBus("Master"))
        for name in ("Music", "SFX", "Ambient", "Voice"):
            self.create_bus(name, parent="Master")

    @staticmethod
    def _key(name: str) -> str:
        key = str(name).strip().casefold()
        if not key:
            raise ValueError("Audio bus name must not be empty.")
        return key

    @property
    def buses(self) -> tuple[AudioBus, ...]:
        return tuple(self._buses.values())

    @property
    def sends(self) -> tuple[AudioSend, ...]:
        return tuple(self._sends.values())

    @property
    def master(self) -> AudioBus:
        return self.get_bus("Master")

    @property
    def headroom_db(self) -> float:
        return self._headroom_db

    @headroom_db.setter
    def headroom_db(self, value: float) -> None:
        value = float(value)
        if value > 0.0:
            raise ValueError("Mixer headroom_db must be <= 0.0 dB.")
        self._headroom_db = value

    @property
    def headroom_gain(self) -> float:
        return math.pow(10.0, self._headroom_db / 20.0)

    @property
    def master_limiter_enabled(self) -> bool:
        return self._master_limiter is not None and self._master_limiter.enabled

    @property
    def master_limiter(self) -> LimiterEffect | None:
        return self._master_limiter

    def enable_master_limiter(self, threshold: float = 0.98) -> LimiterEffect:
        if self._master_limiter is None:
            self._master_limiter = LimiterEffect(threshold)
        else:
            self._master_limiter.threshold = threshold
            self._master_limiter.enabled = True
        return self._master_limiter

    def disable_master_limiter(self) -> None:
        if self._master_limiter is not None:
            self._master_limiter.enabled = False

    def has_bus(self, name_or_id: str) -> bool:
        value = str(name_or_id)
        return value in self._buses_by_id or self._key(value) in self._buses

    def add_bus(self, bus: AudioBus) -> AudioBus:
        if not isinstance(bus, AudioBus):
            raise TypeError("bus must be an AudioBus.")
        key = self._key(bus.name)
        if key in self._buses:
            raise ValueError(f"Audio bus already exists: {bus.name}")
        if bus.id in self._buses_by_id:
            raise ValueError(f"Audio bus id already exists: {bus.id}")
        if bus.parent is not None and bus.parent.id not in self._buses_by_id:
            raise ValueError("Parent audio bus must be registered first.")
        self._buses[key] = bus
        self._buses_by_id[bus.id] = bus
        return bus

    def create_bus(
        self,
        name: str,
        *,
        parent: str | AudioBus | None = "Master",
        volume: float = 1.0,
        muted: bool = False,
        pan: float = 0.0,
        solo: bool = False,
        bus_id: str | None = None,
    ) -> AudioBus:
        parent_bus = self.resolve_optional_bus(parent)
        bus = AudioBus(
            name,
            volume=volume,
            muted=muted,
            parent=parent_bus,
            pan=pan,
            solo=solo,
            bus_id=bus_id,
        )
        return self.add_bus(bus)

    def resolve_optional_bus(self, bus: AudioBus | str | None) -> AudioBus | None:
        if bus is None:
            return None
        if isinstance(bus, AudioBus):
            if bus.id in self._buses_by_id:
                return self._buses_by_id[bus.id]
            return self.get_bus(bus.name)
        return self.get_bus(bus)

    def resolve_bus(self, bus: AudioBus | str | None) -> AudioBus:
        return self.resolve_optional_bus(bus) or self.master

    def get_bus(self, name_or_id: str) -> AudioBus:
        value = str(name_or_id)
        by_id = self._buses_by_id.get(value)
        if by_id is not None:
            return by_id
        try:
            return self._buses[self._key(value)]
        except KeyError:
            raise KeyError(f"Unknown audio bus: {name_or_id}") from None

    def get_bus_by_id(self, bus_id: str) -> AudioBus:
        try:
            return self._buses_by_id[str(bus_id)]
        except KeyError:
            raise KeyError(f"Unknown audio bus id: {bus_id}") from None

    def get_buses(self) -> tuple[AudioBus, ...]:
        return self.buses

    def rename_bus(self, name_or_id: str, new_name: str) -> AudioBus:
        bus = self.get_bus(name_or_id)
        if bus is self.master:
            raise ValueError("The master audio bus cannot be renamed.")
        new_name = str(new_name).strip()
        new_key = self._key(new_name)
        old_key = self._key(bus.name)
        if new_key != old_key and new_key in self._buses:
            raise ValueError(f"Audio bus already exists: {new_name}")
        del self._buses[old_key]
        bus.name = new_name
        self._buses[new_key] = bus
        return bus

    def set_bus_parent(self, name_or_id: str, parent: str | AudioBus | None) -> None:
        bus = self.get_bus(name_or_id)
        if bus is self.master:
            if parent is not None:
                raise ValueError("The master audio bus cannot have a parent.")
            return
        old_parent = bus.parent
        bus.parent = self.resolve_optional_bus(parent)
        try:
            self._validate_routing_graph()
        except Exception:
            bus.parent = old_parent
            raise

    def remove_bus(
        self,
        name_or_id: str,
        *,
        reparent_children_to: str | AudioBus | None = "Master",
    ) -> AudioBus:
        bus = self.get_bus(name_or_id)
        if bus is self.master:
            raise ValueError("The master audio bus cannot be removed.")

        replacement = self.resolve_optional_bus(reparent_children_to)
        if replacement is bus:
            replacement = bus.parent

        for child in self._buses.values():
            if child.parent is bus:
                child.parent = replacement

        for send_id, send in tuple(self._sends.items()):
            if send.source_bus_id == bus.id or send.target_bus_id == bus.id:
                del self._sends[send_id]

        del self._buses[self._key(bus.name)]
        del self._buses_by_id[bus.id]
        self._validate_routing_graph()
        return bus

    # ------------------------------------------------------------------
    # Sends / returns
    # ------------------------------------------------------------------

    def add_send(
        self,
        source: str | AudioBus,
        target: str | AudioBus,
        *,
        amount: float = 1.0,
        pre_fader: bool = False,
        enabled: bool = True,
        send_id: str | None = None,
    ) -> AudioSend:
        source_bus = self.resolve_bus(source)
        target_bus = self.resolve_bus(target)
        if source_bus is target_bus:
            raise ValueError("An audio bus cannot send to itself.")
        send = AudioSend(
            source_bus.id,
            target_bus.id,
            amount=amount,
            pre_fader=pre_fader,
            enabled=enabled,
            **({"id": str(send_id)} if send_id else {}),
        )
        self._sends[send.id] = send
        try:
            self._validate_routing_graph()
        except Exception:
            del self._sends[send.id]
            raise
        return send

    def remove_send(self, send_or_id: AudioSend | str) -> None:
        send_id = send_or_id.id if isinstance(send_or_id, AudioSend) else str(send_or_id)
        if send_id not in self._sends:
            raise KeyError(f"Unknown audio send: {send_id}")
        del self._sends[send_id]

    def get_send(self, send_id: str) -> AudioSend:
        try:
            return self._sends[str(send_id)]
        except KeyError:
            raise KeyError(f"Unknown audio send: {send_id}") from None

    def get_sends_from(self, bus: str | AudioBus) -> tuple[AudioSend, ...]:
        bus_id = self.resolve_bus(bus).id
        return tuple(send for send in self._sends.values() if send.source_bus_id == bus_id)

    def set_send_amount(self, send_id: str, amount: float) -> None:
        self.get_send(send_id).amount = amount

    def set_send_enabled(self, send_id: str, enabled: bool) -> None:
        send = self.get_send(send_id)
        old = send.enabled
        send.enabled = bool(enabled)
        try:
            self._validate_routing_graph()
        except Exception:
            send.enabled = old
            raise

    def set_send_pre_fader(self, send_id: str, pre_fader: bool) -> None:
        self.get_send(send_id).pre_fader = bool(pre_fader)

    # ------------------------------------------------------------------
    # Graph ordering / solo
    # ------------------------------------------------------------------

    def _routing_edges(self) -> dict[str, set[str]]:
        edges = {bus.id: set() for bus in self._buses.values()}
        for bus in self._buses.values():
            if bus is self.master:
                continue
            target = bus.parent or self.master
            edges[bus.id].add(target.id)
        for send in self._sends.values():
            if send.enabled:
                edges[send.source_bus_id].add(send.target_bus_id)
        return edges

    def _validate_routing_graph(self) -> None:
        self.processing_order()

    def processing_order(self) -> tuple[AudioBus, ...]:
        """Return source-before-destination topological routing order."""
        edges = self._routing_edges()
        indegree = {bus_id: 0 for bus_id in edges}
        for targets in edges.values():
            for target in targets:
                indegree[target] += 1

        queue = [bus.id for bus in self._buses.values() if indegree[bus.id] == 0]
        ordered: list[AudioBus] = []
        while queue:
            bus_id = queue.pop(0)
            ordered.append(self._buses_by_id[bus_id])
            for target in edges[bus_id]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)

        if len(ordered) != len(self._buses):
            raise ValueError("Audio routing graph cannot contain feedback cycles.")
        return tuple(ordered)

    def buses_by_depth(self, *, deepest_first: bool = False) -> tuple[AudioBus, ...]:
        ordered = self.processing_order()
        return ordered if deepest_first else tuple(reversed(ordered))

    @property
    def solo_active(self) -> bool:
        return any(bus.solo for bus in self._buses.values())

    @staticmethod
    def _is_ancestor(ancestor: AudioBus, bus: AudioBus) -> bool:
        current = bus.parent
        while current is not None:
            if current is ancestor:
                return True
            current = current.parent
        return False

    def is_bus_audible(self, bus: AudioBus) -> bool:
        soloed = tuple(candidate for candidate in self._buses.values() if candidate.solo)
        if not soloed:
            return True

        # Preserve the established solo behaviour for the full hierarchy branch
        # and additionally keep downstream send/return targets alive. Otherwise
        # soloing Weapons would silence the Reverb return fed by Weapons.
        audible_ids: set[str] = set()
        for candidate in soloed:
            for branch_bus in self._buses.values():
                if (
                    branch_bus is candidate
                    or self._is_ancestor(branch_bus, candidate)
                    or self._is_ancestor(candidate, branch_bus)
                ):
                    audible_ids.add(branch_bus.id)

        edges = self._routing_edges()
        queue = list(audible_ids)
        while queue:
            source_id = queue.pop()
            for target_id in edges[source_id]:
                if target_id not in audible_ids:
                    audible_ids.add(target_id)
                    queue.append(target_id)

        return bus.id in audible_ids

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def create_snapshot(self) -> dict[str, Any]:
        return deepcopy({
            "version": self.SNAPSHOT_VERSION,
            "headroom_db": self.headroom_db,
            "master_limiter": None if self._master_limiter is None else self._master_limiter.to_state(),
            "buses": [
                {
                    "id": bus.id,
                    "name": bus.name,
                    "parent_id": None if bus.parent is None else bus.parent.id,
                    "volume": bus.volume,
                    "muted": bus.muted,
                    "pan": bus.pan,
                    "solo": bus.solo,
                    "effects_bypassed": bus.effects_bypassed,
                    "effects": [effect.to_state() for effect in bus.effects],
                }
                for bus in self._buses.values()
            ],
            "sends": [
                {
                    "id": send.id,
                    "source_bus_id": send.source_bus_id,
                    "target_bus_id": send.target_bus_id,
                    "amount": send.amount,
                    "pre_fader": send.pre_fader,
                    "enabled": send.enabled,
                }
                for send in self._sends.values()
            ],
        })

    def restore_snapshot(self, snapshot: dict[str, Any], *, restore_topology: bool = True) -> None:
        data = deepcopy(snapshot)
        if int(data.get("version", 0)) != self.SNAPSHOT_VERSION:
            raise ValueError("Unsupported audio mixer snapshot version.")

        bus_states = list(data.get("buses") or [])
        if not bus_states:
            raise ValueError("Mixer snapshot contains no buses.")

        master_state = next((state for state in bus_states if str(state.get("name", "")).casefold() == "master"), None)
        if master_state is None:
            raise ValueError("Mixer snapshot must contain Master bus.")

        snapshot_to_runtime: dict[str, str] = {str(master_state["id"]): self.master.id}

        if restore_topology:
            wanted_ids = {str(state["id"]) for state in bus_states if state is not master_state}
            for bus in tuple(self._buses.values()):
                if bus is not self.master and bus.id not in wanted_ids:
                    self.remove_bus(bus.id)

        # First pass: make sure all buses exist and names are restored.
        for state in bus_states:
            snapshot_id = str(state["id"])
            if state is master_state:
                bus = self.master
            elif snapshot_id in self._buses_by_id:
                bus = self._buses_by_id[snapshot_id]
            elif restore_topology:
                bus = self.create_bus(str(state["name"]), parent=None, bus_id=snapshot_id)
            else:
                try:
                    bus = self.get_bus(str(state["name"]))
                except KeyError:
                    continue
            snapshot_to_runtime[snapshot_id] = bus.id
            if bus.name != str(state["name"]):
                self.rename_bus(bus.id, str(state["name"]))

        # Parent relations after all buses exist.
        for state in bus_states:
            snapshot_id = str(state["id"])
            runtime_id = snapshot_to_runtime.get(snapshot_id)
            if runtime_id is None:
                continue
            bus = self.get_bus_by_id(runtime_id)
            if bus is self.master:
                bus.parent = None
            else:
                parent_snapshot_id = state.get("parent_id")
                if parent_snapshot_id is None:
                    bus.parent = None
                else:
                    parent_runtime_id = snapshot_to_runtime[str(parent_snapshot_id)]
                    bus.parent = self.get_bus_by_id(parent_runtime_id)

            bus.volume = float(state.get("volume", 1.0))
            bus.muted = bool(state.get("muted", False))
            bus.pan = float(state.get("pan", 0.0))
            bus.solo = bool(state.get("solo", False))
            bus.effects_bypassed = bool(state.get("effects_bypassed", False))
            bus.clear_effects()
            for effect_state in state.get("effects") or []:
                try:
                    bus.add_effect(audio_effect_from_state(effect_state))
                except ValueError:
                    # Custom effect types cannot be recreated safely without a
                    # registered factory. Built-in Nexora effects are complete.
                    continue

        self._sends.clear()
        for state in data.get("sends") or []:
            source_id = snapshot_to_runtime.get(str(state["source_bus_id"]))
            target_id = snapshot_to_runtime.get(str(state["target_bus_id"]))
            if source_id is None or target_id is None:
                continue
            self.add_send(
                source_id,
                target_id,
                amount=float(state.get("amount", 1.0)),
                pre_fader=bool(state.get("pre_fader", False)),
                enabled=bool(state.get("enabled", True)),
                send_id=str(state["id"]),
            )

        self.headroom_db = float(data.get("headroom_db", 0.0))
        limiter_state = data.get("master_limiter")
        if limiter_state is None:
            self._master_limiter = None
        else:
            effect = audio_effect_from_state(limiter_state)
            if not isinstance(effect, LimiterEffect):
                raise ValueError("Snapshot master_limiter is not a limiter.")
            self._master_limiter = effect

        self._validate_routing_graph()

    def reset(self) -> None:
        self._sends.clear()
        self.headroom_db = 0.0
        self._master_limiter = None
        for bus in self._buses.values():
            bus.volume = 1.0
            bus.muted = False
            bus.pan = 0.0
            bus.solo = False
            bus.effects_bypassed = False
            bus.reset_meter()
            bus.reset_effects()
