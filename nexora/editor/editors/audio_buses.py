from __future__ import annotations

"""Bus selection, routing and mixer-control synchronization for the audio editor."""


class AudioBusMixin:
    def _selected_bus(self):
        if self._selected_bus_id is None:
            return None
        try:
            return self.game.audio.get_bus_by_id(self._selected_bus_id)
        except KeyError:
            return None

    def _refresh_bus_list(self, *, select_name: str | None = None) -> None:
        buses = self.game.audio.get_buses()
        items = []
        selected_index = -1
        for index, bus in enumerate(buses):
            parent = bus.parent.name if bus.parent is not None else "—"
            prefix = "◆" if bus.name.casefold() == "master" else "•"
            items.append(f"{prefix} {bus.name}  →  {parent}")
            if (select_name and bus.name.casefold() == select_name.casefold()) or bus.id == self._selected_bus_id:
                selected_index = index
        self.bus_list.set_items(items)
        if selected_index < 0 and buses:
            selected_index = 0
        if selected_index >= 0:
            self.bus_list.selected = selected_index
            self._selected_bus_id = buses[selected_index].id
        self._sync_controls()

    def _sync_controls(self) -> None:
        bus = self._selected_bus()
        if bus is None:
            return
        self._syncing = True
        try:
            self.rename_field.set_text(bus.name)
            self.volume_slider.value = bus.volume
            self.pan_slider.value = bus.pan
            self.mute_check.checked = bus.muted
            self.solo_check.checked = bus.solo
            self.bypass_chain_check.checked = bus.effects_bypassed
            parents = [candidate.name for candidate in self.game.audio.get_buses() if candidate is not bus]
            if bus.name.casefold() == "master":
                parents = ["—"]
            elif "Master" not in parents:
                parents.insert(0, "Master")
            self.parent_dropdown.options = tuple(parents or ["—"])
            parent_name = bus.parent.name if bus.parent is not None else "Master"
            if bus.name.casefold() == "master":
                parent_name = "—"
            try:
                self.parent_dropdown.selected = self.parent_dropdown.options.index(parent_name)
            except ValueError:
                self.parent_dropdown.selected = 0

            self.effect_list.set_items([
                f"{index + 1}. {type(effect).__name__}  wet {effect.wet:.0%}{'  [BYPASS]' if effect.bypassed else ''}"
                for index, effect in enumerate(bus.effects)
            ])
            if self._selected_effect >= len(bus.effects):
                self._selected_effect = len(bus.effects) - 1
            self.effect_list.selected = self._selected_effect
            effect = bus.effects[self._selected_effect] if 0 <= self._selected_effect < len(bus.effects) else None
            self.effect_bypass_check.checked = bool(effect.bypassed) if effect is not None else False
            self.effect_wet_slider.value = effect.wet if effect is not None else 1.0
            self.effect_bypass_check.enabled = effect is not None
            self.effect_wet_slider.enabled = effect is not None
            self.remove_effect_button.enabled = effect is not None
            self._effect_parameter_names = []
            parameter_values = {} if effect is None else dict(effect.to_state().get("parameters") or {})
            for slot, field in enumerate(self.effect_parameter_fields):
                if slot < len(parameter_values):
                    parameter, value = list(parameter_values.items())[slot]
                    self._effect_parameter_names.append(parameter)
                    field.set_text(str(value))
                    field.enabled = True
                    field.visible = True
                else:
                    field.set_text("")
                    field.enabled = False
                    field.visible = False

            sends = self.game.audio.mixer.get_sends_from(bus)
            send_items = []
            for send in sends:
                target = self.game.audio.get_bus_by_id(send.target_bus_id)
                mode = "pre" if send.pre_fader else "post"
                send_items.append(f"{target.name}  {send.amount:.2f}  {mode}{'' if send.enabled else ' [off]'}")
            self.send_list.set_items(send_items)
            if self._selected_send >= len(sends):
                self._selected_send = len(sends) - 1
            self.send_list.selected = self._selected_send
            selected_send = sends[self._selected_send] if 0 <= self._selected_send < len(sends) else None
            self.send_enabled_check.enabled = selected_send is not None
            self.remove_send_button.enabled = selected_send is not None
            if selected_send is not None:
                self.send_enabled_check.checked = selected_send.enabled
                self.send_amount_slider.value = selected_send.amount
                self.send_pre_check.checked = selected_send.pre_fader

            targets = [candidate.name for candidate in self.game.audio.get_buses() if candidate is not bus]
            self.send_target_dropdown.options = tuple(targets or ["Master"])
            self.send_target_dropdown.selected = min(self.send_target_dropdown.selected, len(self.send_target_dropdown.options) - 1)
            self.remove_bus_button.enabled = bus.name.casefold() != "master"
            self.rename_button.enabled = bus.name.casefold() != "master"
            self.rename_field.enabled = bus.name.casefold() != "master"
            self.parent_dropdown.enabled = bus.name.casefold() != "master"
        finally:
            self._syncing = False

    def _bus_selected(self, index: int) -> None:
        buses = self.game.audio.get_buses()
        if 0 <= index < len(buses):
            self._selected_bus_id = buses[index].id
            self._selected_effect = -1
            self._selected_send = -1
            self._sync_controls()

    def _add_bus(self) -> None:
        name = self.add_bus_name.text.strip()
        if not name:
            self.status = "Enter a bus name."
            return
        try:
            parent = self._selected_bus() or self.game.audio.mixer.master
            self.game.audio.create_bus(name, parent=parent)
            self.add_bus_name.set_text("")
            self.status = f"Created bus {name}."
            self._refresh_bus_list(select_name=name)
        except Exception as exc:
            self.status = f"Bus error: {exc}"

    def _remove_bus(self) -> None:
        bus = self._selected_bus()
        if bus is None or bus.name.casefold() == "master":
            return
        name = bus.name
        try:
            parent = bus.parent.name if bus.parent is not None else "Master"
            self.game.audio.remove_bus(name, reassign_to=parent, reparent_children=True)
            self._selected_bus_id = None
            self.status = f"Removed bus {name}."
            self._refresh_bus_list(select_name=parent)
        except Exception as exc:
            self.status = f"Remove failed: {exc}"

    def _rename_bus(self) -> None:
        bus = self._selected_bus()
        if bus is None or bus.name.casefold() == "master":
            return
        new_name = self.rename_field.text.strip()
        if not new_name:
            return
        try:
            self.game.audio.rename_bus(bus.id, new_name)
            self.status = f"Renamed bus to {new_name}."
            self._refresh_bus_list(select_name=new_name)
        except Exception as exc:
            self.status = f"Rename failed: {exc}"

    def _parent_changed(self, _index: int, value: str) -> None:
        if self._syncing:
            return
        bus = self._selected_bus()
        if bus is None or bus.name.casefold() == "master":
            return
        try:
            self.game.audio.set_bus_parent(bus.name, value)
            self.status = f"{bus.name} → {value}"
            self._refresh_bus_list(select_name=bus.name)
        except Exception as exc:
            self.status = f"Routing rejected: {exc}"
            self._sync_controls()

    def _volume_changed(self, value: float) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.volume = value

    def _pan_changed(self, value: float) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.pan = value

    def _mute_changed(self, value: bool) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.muted = value

    def _solo_changed(self, value: bool) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.solo = value

    def _chain_bypass_changed(self, value: bool) -> None:
        bus = self._selected_bus()
        if bus is not None and not self._syncing:
            bus.effects_bypassed = value

    def _clear_peak(self) -> None:
        bus = self._selected_bus()
        if bus is not None:
            bus.clear_peak_hold()
