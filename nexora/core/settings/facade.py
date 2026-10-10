from __future__ import annotations

from copy import deepcopy
from typing import Any


class SettingsFacade:
    """Shared runtime behavior for layered Nexora settings facades."""

    KEY_LABEL = "Setting"
    VALIDATE_KEY_TYPE = True

    def _initialize_settings(self, store, *, autosave: bool) -> None:
        self.store = store
        self.autosave = bool(autosave)
        self._data: dict[str, Any] = {}
        self._user_data: dict[str, Any] = {}
        self.reload()

    @property
    def data(self) -> dict[str, Any]:
        return deepcopy(self._data)

    @property
    def user_data(self) -> dict[str, Any]:
        return deepcopy(self._user_data)

    @property
    def settings_path(self):
        return self.store.settings_path

    def reload(self) -> None:
        self._data = self.store.load()
        self._user_data = self.store.load_user()

    def get(self, key: str, default: Any = None) -> Any:
        current: Any = self._data
        for part in self._split_key(key):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, key: str, value: Any) -> None:
        parts = self._split_key(key)
        self._set_nested(self._user_data, parts, value)

        if self.autosave:
            self.save()
        else:
            self._set_nested(self._data, parts, value)

    def save(self) -> None:
        self.store.save_user(self._user_data)
        self.reload()

    def reset_user(self) -> None:
        self.store.reset_user()
        self.reload()

    def remove_override(self, key: str) -> bool:
        parts = self._split_key(key)
        current = self._user_data

        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                return False
            current = child

        final = parts[-1]
        if final not in current:
            return False

        del current[final]
        self._remove_empty_sections(self._user_data)

        if self.autosave:
            self.save()
        else:
            self.reload()

        return True

    @classmethod
    def _split_key(cls, key: str) -> list[str]:
        if cls.VALIDATE_KEY_TYPE and not isinstance(key, str):
            raise TypeError(f"{cls.KEY_LABEL} setting key must be a string.")

        parts = [part for part in key.split(".") if part]
        if not parts:
            raise ValueError(f"{cls.KEY_LABEL} setting key cannot be empty.")
        return parts

    @staticmethod
    def _set_nested(
        target: dict[str, Any],
        parts: list[str],
        value: Any,
    ) -> None:
        current = target
        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = child
        current[parts[-1]] = value

    @classmethod
    def _remove_empty_sections(cls, data: dict[str, Any]) -> None:
        for key in list(data):
            value = data[key]
            if isinstance(value, dict):
                cls._remove_empty_sections(value)
                if not value:
                    del data[key]
