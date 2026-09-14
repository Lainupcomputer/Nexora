from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import (
    Generic,
    Iterable,
    TypeVar,
)

from nexora.core.paths import (
    ProjectPaths,
)


T = TypeVar(
    "T"
)


# Sentinel:
#
# omitted settings_path
#     -> Documents/<project>/settings
#
# explicit settings_path=None
#     -> no user settings
#
# Das ist vor allem für Tests praktisch.
_AUTO_PATH = object()


class LayeredSettingsStore(
    ABC,
    Generic[T],
):
    """
    Common layered settings storage.

    Layer order:

        Nexora defaults
            ↓
        project overrides
            ↓
        mod overrides
            ↓
        user overrides

    Later layers override earlier layers.

    Concrete stores decide:

        - how a file is decoded
        - how layers are merged
        - how user data is encoded
        - how values are validated

    Therefore graphics settings may deep-merge while key
    bindings may replace complete actions.
    """

    FILE_NAME = ""

    USER_HEADER = (
        "# Nexora user settings\n"
        "# Only changed values are stored here.\n"
    )

    def __init__(
        self,
        *,
        project_name: str = "Nexora",
        defaults_path: (
            str | Path | None
        ) = None,
        project_path: (
            str | Path | None
        ) = None,
        mod_paths: Iterable[
            str | Path
        ] = (),
        settings_path=_AUTO_PATH,
    ) -> None:
        if not self.FILE_NAME:
            raise RuntimeError(
                "LayeredSettingsStore subclasses must "
                "define FILE_NAME."
            )

        # ======================================================
        # Project paths
        # ======================================================

        self.project_paths = (
            ProjectPaths(
                project_name
            )
        )

        self.project_name = (
            self.project_paths.project_name
        )

        # ======================================================
        # Defaults
        #
        # Normal Nexora usage always resolves automatically to:
        #
        # nexora/core/defaults/<FILE_NAME>
        #
        # defaults_path remains supported internally/tests.
        # ======================================================

        self.defaults_path = (
            Path(
                defaults_path
            )
            if defaults_path is not None
            else self.project_paths.default_file(
                self.FILE_NAME
            )
        )

        # ======================================================
        # Optional project layer
        # ======================================================

        self.project_path = (
            Path(
                project_path
            )
            if project_path is not None
            else None
        )

        # ======================================================
        # Optional mod layers
        # ======================================================

        self.mod_paths = tuple(
            Path(
                path
            )
            for path in mod_paths
        )

        # ======================================================
        # User settings
        # ======================================================

        if (
            settings_path
            is _AUTO_PATH
        ):
            self.settings_path = (
                self.project_paths.settings
            )

        elif settings_path is None:
            self.settings_path = None

        else:
            self.settings_path = (
                Path(
                    settings_path
                )
            )

        self.user_path = (
            (
                self.settings_path
                / self.FILE_NAME
            )
            if self.settings_path
            is not None
            else None
        )

    # ==========================================================
    # USER FILE
    # ==========================================================

    def ensure_user_file(
        self,
    ) -> None:
        """
        Create an empty override file.

        Defaults are never copied into the user's configuration.
        """

        path = (
            self.user_path
        )

        if path is None:
            return

        if path.exists():
            return

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            self.USER_HEADER,
            encoding="utf-8",
        )

    # ==========================================================
    # LOAD
    # ==========================================================

    def load(
        self,
    ) -> T:
        """
        Load the complete effective configuration.
        """

        self.ensure_user_file()

        result = (
            self._load_layers(
                include_user=True
            )
        )

        self._validate_complete(
            result
        )

        return result

    def load_without_user(
        self,
    ) -> T:
        """
        Load defaults + project + mods.

        Useful when calculating which values actually need to
        be stored as user overrides.
        """

        result = (
            self._load_layers(
                include_user=False
            )
        )

        self._validate_complete(
            result
        )

        return result

    def load_user(
        self,
    ) -> T:
        """
        Load only the user override layer.
        """

        self.ensure_user_file()

        if self.user_path is None:
            return self._empty()

        return self._read_layer(
            self.user_path,
            required=False,
        )

    def _load_layers(
        self,
        *,
        include_user: bool,
    ) -> T:
        # ------------------------------------------------------
        # Engine defaults
        # ------------------------------------------------------

        result = (
            self._read_layer(
                self.defaults_path,
                required=True,
            )
        )

        # ------------------------------------------------------
        # Project
        # ------------------------------------------------------

        if self.project_path is not None:
            layer = (
                self._read_layer(
                    self.project_path,
                    required=False,
                )
            )

            self._merge_layer(
                result,
                layer,
            )

        # ------------------------------------------------------
        # Mods
        # ------------------------------------------------------

        for path in self.mod_paths:
            layer = (
                self._read_layer(
                    path,
                    required=False,
                )
            )

            self._merge_layer(
                result,
                layer,
            )

        # ------------------------------------------------------
        # User
        # ------------------------------------------------------

        if (
            include_user
            and self.user_path
            is not None
        ):
            layer = (
                self._read_layer(
                    self.user_path,
                    required=False,
                )
            )

            self._merge_layer(
                result,
                layer,
            )

        return result

    # ==========================================================
    # SAVE
    # ==========================================================

    def save_user(
        self,
        data: T,
    ) -> None:
        """
        Save the user override layer atomically.
        """

        if self.user_path is None:
            raise RuntimeError(
                "No user settings path is configured."
            )

        self._validate_user(
            data
        )

        content = (
            self._encode_user(
                data
            )
        )

        self._write_user_text(
            content
        )

    def _write_user_text(
        self,
        content: str,
    ) -> None:
        path = (
            self.user_path
        )

        if path is None:
            raise RuntimeError(
                "No user settings path is configured."
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = (
            path.with_suffix(
                path.suffix
                + ".tmp"
            )
        )

        temporary.write_text(
            content,
            encoding="utf-8",
        )

        temporary.replace(
            path
        )

    # ==========================================================
    # RESET
    # ==========================================================

    def reset_user(
        self,
    ) -> None:
        """
        Remove all user overrides.
        """

        if self.user_path is None:
            return

        if self.user_path.exists():
            self.user_path.unlink()

        self.ensure_user_file()

    # ==========================================================
    # IMPLEMENTATION HOOKS
    # ==========================================================

    @abstractmethod
    def _empty(
        self,
    ) -> T:
        """
        Create an empty settings layer.
        """

        raise NotImplementedError

    @abstractmethod
    def _read_layer(
        self,
        path: Path,
        *,
        required: bool,
    ) -> T:
        raise NotImplementedError

    @abstractmethod
    def _merge_layer(
        self,
        target: T,
        source: T,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def _encode_user(
        self,
        data: T,
    ) -> str:
        raise NotImplementedError

    def _validate_user(
        self,
        data: T,
    ) -> None:
        """
        Optional user-layer validation hook.
        """

    def _validate_complete(
        self,
        data: T,
    ) -> None:
        """
        Optional effective-config validation hook.
        """