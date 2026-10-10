from __future__ import annotations

"""Aux-send editing for the audio editor."""


class AudioSendsMixin:
    def _send_selected(self, index: int) -> None:
        self._selected_send = index
        self._sync_controls()

    def _add_send(self) -> None:
        bus = self._selected_bus()
        if bus is None or not self.send_target_dropdown.value:
            return
        try:
            self.game.audio.add_send(
                bus,
                self.send_target_dropdown.value,
                amount=self.send_amount_slider.value,
                pre_fader=self.send_pre_check.checked,
            )
            self.status = f"Added send {bus.name} → {self.send_target_dropdown.value}."
            self._selected_send = -1
            self._sync_controls()
        except Exception as exc:
            self.status = f"Send rejected: {exc}"

    def _remove_send(self) -> None:
        bus = self._selected_bus()
        if bus is None:
            return
        sends = self.game.audio.mixer.get_sends_from(bus)
        if not (0 <= self._selected_send < len(sends)):
            return
        self.game.audio.remove_send(sends[self._selected_send])
        self._selected_send = -1
        self.status = "Removed send."
        self._sync_controls()

    def _send_enabled_changed(self, enabled: bool) -> None:
        bus = self._selected_bus()
        if bus is None or self._syncing:
            return
        sends = self.game.audio.mixer.get_sends_from(bus)
        if 0 <= self._selected_send < len(sends):
            try:
                self.game.audio.set_send_enabled(sends[self._selected_send].id, enabled)
            except Exception as exc:
                self.status = f"Send rejected: {exc}"
                self._sync_controls()

    def _send_amount_changed(self, amount: float) -> None:
        bus = self._selected_bus()
        if bus is None or self._syncing:
            return
        sends = self.game.audio.mixer.get_sends_from(bus)
        if 0 <= self._selected_send < len(sends):
            self.game.audio.set_send_amount(sends[self._selected_send].id, amount)

    def _send_pre_changed(self, pre_fader: bool) -> None:
        bus = self._selected_bus()
        if bus is None or self._syncing:
            return
        sends = self.game.audio.mixer.get_sends_from(bus)
        if 0 <= self._selected_send < len(sends):
            self.game.audio.set_send_pre_fader(sends[self._selected_send].id, pre_fader)
            self._sync_controls()
