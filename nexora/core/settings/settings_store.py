from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


class SettingsStore:
    """
    Persistent key/value settings store.

    Supports dotted keys:

        "video.vsync"
        "video.fullscreen"
        "audio.master_volume"

    Data is stored as JSON.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        defaults: dict[str, Any] | None = None,
        autosave: bool = False,
    ) -> None:
        self.path = Path(
            path
        )

        self.autosave = bool(
            autosave
        )

        self._defaults: dict[
            str,
            Any,
        ] = deepcopy(
            defaults
            if defaults is not None
            else {}
        )

        self._data: dict[
            str,
            Any,
        ] = {}

        self.reload()

    # ==============================================================
    # Data
    # ==============================================================

    @property
    def data(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return deepcopy(
            self._data
        )

    @property
    def defaults(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return deepcopy(
            self._defaults
        )

    # ==============================================================
    # Get
    # ==============================================================

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Get a setting using a dotted key.

        Example:

            settings.get(
                "audio.master_volume",
                1.0,
            )
        """

        parts = self._split_key(
            key
        )

        current: Any = (
            self._data
        )

        for part in parts:
            if not isinstance(
                current,
                dict,
            ):
                return default

            if part not in current:
                return default

            current = current[
                part
            ]

        return current

    # ==============================================================
    # Set
    # ==============================================================

    def set(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Set a value using a dotted key.
        """

        parts = self._split_key(
            key
        )

        current = self._data

        for part in parts[
            :-1
        ]:
            existing = current.get(
                part
            )

            if not isinstance(
                existing,
                dict,
            ):
                existing = {}

                current[
                    part
                ] = existing

            current = existing

        current[
            parts[-1]
        ] = value

        if self.autosave:
            self.save()

    # ==============================================================
    # Contains
    # ==============================================================

    def contains(
        self,
        key: str,
    ) -> bool:
        sentinel = object()

        return (
            self.get(
                key,
                sentinel,
            )
            is not sentinel
        )

    def __contains__(
        self,
        key: str,
    ) -> bool:
        return self.contains(
            key
        )

    # ==============================================================
    # Remove
    # ==============================================================

    def remove(
        self,
        key: str,
    ) -> bool:
        parts = self._split_key(
            key
        )

        current = self._data

        for part in parts[
            :-1
        ]:
            value = current.get(
                part
            )

            if not isinstance(
                value,
                dict,
            ):
                return False

            current = value

        final_key = parts[-1]

        if final_key not in current:
            return False

        del current[
            final_key
        ]

        if self.autosave:
            self.save()

        return True

    # ==============================================================
    # Defaults
    # ==============================================================

    def get_default(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        parts = self._split_key(
            key
        )

        current: Any = (
            self._defaults
        )

        for part in parts:
            if not isinstance(
                current,
                dict,
            ):
                return default

            if part not in current:
                return default

            current = current[
                part
            ]

        return deepcopy(
            current
        )

    def set_default(
        self,
        key: str,
        value: Any,
    ) -> None:
        parts = self._split_key(
            key
        )

        current = (
            self._defaults
        )

        for part in parts[
            :-1
        ]:
            existing = current.get(
                part
            )

            if not isinstance(
                existing,
                dict,
            ):
                existing = {}

                current[
                    part
                ] = existing

            current = existing

        current[
            parts[-1]
        ] = deepcopy(
            value
        )

    # ==============================================================
    # Reset
    # ==============================================================

    def reset(
        self,
        *,
        save: bool = True,
    ) -> None:
        """
        Reset all values to defaults.
        """

        self._data = deepcopy(
            self._defaults
        )

        if save:
            self.save()

    def reset_key(
        self,
        key: str,
    ) -> bool:
        """
        Reset one setting to its default.

        Returns False if no default exists for the key.
        """

        sentinel = object()

        default = self.get_default(
            key,
            sentinel,
        )

        if default is sentinel:
            return False

        self.set(
            key,
            default,
        )

        return True

    # ==============================================================
    # Persistence
    # ==============================================================

    def save(
        self,
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self._data,
                file,
                indent=4,
                ensure_ascii=False,
                sort_keys=True,
            )

    def reload(
        self,
    ) -> None:
        """
        Reload settings from disk.

        Defaults are always used as the base.
        """

        self._data = deepcopy(
            self._defaults
        )

        if not self.path.is_file():
            return

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            loaded = json.load(
                file
            )

        if not isinstance(
            loaded,
            dict,
        ):
            raise ValueError(
                "Settings file root must be a JSON object."
            )

        self._merge_dict(
            self._data,
            loaded,
        )

    # ==============================================================
    # Helpers
    # ==============================================================

    @staticmethod
    def _split_key(
        key: str,
    ) -> tuple[
        str,
        ...,
    ]:
        if not isinstance(
            key,
            str,
        ):
            raise TypeError(
                "settings key must be a string."
            )

        key = key.strip()

        if not key:
            raise ValueError(
                "settings key cannot be empty."
            )

        parts = tuple(
            part.strip()
            for part in key.split(
                "."
            )
        )

        if any(
            not part
            for part in parts
        ):
            raise ValueError(
                f"Invalid settings key: {key!r}"
            )

        return parts

    @classmethod
    def _merge_dict(
        cls,
        target: dict[
            str,
            Any,
        ],
        source: dict[
            str,
            Any,
        ],
    ) -> None:
        for key, value in source.items():
            if (
                isinstance(
                    value,
                    dict,
                )
                and isinstance(
                    target.get(
                        key
                    ),
                    dict,
                )
            ):
                cls._merge_dict(
                    target[
                        key
                    ],
                    value,
                )

            else:
                target[
                    key
                ] = deepcopy(
                    value
                )

    # ==============================================================
    # Representation
    # ==============================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"SettingsStore("
            f"path={str(self.path)!r}, "
            f"keys={len(self._data)}"
            f")"
        )