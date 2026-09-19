from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from nexora.nodes.ui.containers.panel import Panel
from nexora.nodes.ui.controls.button import Button
from nexora.nodes.ui.output.label import Label
from nexora.nodes.ui.ui_node import UINode
from nexora.signals import Signal


if TYPE_CHECKING:
    from nexora.input.input import InputManager


Callback = Callable[[], None]


class _MenuButton(Button):
    """Button variant whose keyboard input stays action-driven.

    The regular Button control also supports its legacy raw SDL Enter/Space
    path. GameMenu deliberately keeps keyboard control in InputManager so a
    project's action bindings remain authoritative. Mouse interaction and
    focus visuals still use the normal Button implementation.
    """

    def update_input(self, ui_input) -> None:
        if not self.visible or not self.enabled:
            self.hovered = False
            self.pressed = False
            self._press_started_inside = False
            self._keyboard_pressed = False
            self._sync_visuals()
            return

        mouse_x, mouse_y = ui_input.mouse_position
        self.hovered = self.contains_point(mouse_x, mouse_y)

        if ui_input.mouse_left_pressed:
            self._press_started_inside = self.hovered

        mouse_pressed_visual = (
            self._press_started_inside
            and ui_input.mouse_left_down
            and self.hovered
        )

        if ui_input.mouse_left_released:
            should_click = (
                self._press_started_inside
                and self.hovered
            )
            self._press_started_inside = False

            if should_click:
                self.click()

        self._keyboard_pressed = False
        self.pressed = mouse_pressed_visual
        self._sync_visuals()


class GameMenuTab(UINode):
    """Base class for one replaceable tab in :class:`GameMenu`.

    The default tabs are intentionally only presentation shells. A game can
    later replace the contents of one tab or subclass it without changing the
    menu, input or pause logic.
    """

    tab_id = "tab"
    title = "Tab"
    description = "This tab is ready for a game-specific system."

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(name, world)

        self._content_panel = self.create_child(
            "ContentPanel",
            node_type=Panel,
        )
        self._content_panel.background = (
            20,
            23,
            28,
            250,
        )
        self._content_panel.border_color = (
            126,
            86,
            38,
            255,
        )
        self._content_panel.border_width = 1.0
        self._content_panel.border_radius = 4.0

        self._title_label = self.create_child(
            "Title",
            node_type=Label,
        )
        self._title_label.text = self.title
        self._title_label.scale = 1.55
        self._title_label.anchor = (0.5, 0.5)
        self._title_label.pivot = (0.0, 0.5)

        self._description_label = self.create_child(
            "Description",
            node_type=Label,
        )
        self._description_label.text = self.description
        self._description_label.scale = 0.95
        self._description_label.anchor = (0.5, 0.5)
        self._description_label.pivot = (0.0, 0.5)

        self.visible = False

    def _sync_layout(self) -> None:
        width, height = self.size

        self._content_panel.size = (width, height)
        self._content_panel.position = (0.0, 0.0)

        self._title_label.position = (
            -width / 2.0 + 28.0,
            -height / 2.0 + 34.0,
        )

        self._description_label.position = (
            -width / 2.0 + 28.0,
            -height / 2.0 + 82.0,
        )

    def set_description(self, text: str) -> None:
        """Set the small helper text shown below the tab title."""

        self.description = str(text)
        self._description_label.text = self.description

    def render(self, renderer) -> None:
        if not self.visible:
            return

        self._sync_layout()
        super().render(renderer)


class EquipmentTab(GameMenuTab):
    tab_id = "equipment"
    title = "Equipment"
    description = "Equipment slots will be connected here."


class InventoryTab(GameMenuTab):
    tab_id = "inventory"
    title = "Inventory"
    description = "The item grid will be connected here."


class CraftingTab(GameMenuTab):
    tab_id = "crafting"
    title = "Crafting"
    description = "Recipes and crafting stations will be connected here."


class SkillsTab(GameMenuTab):
    tab_id = "skills"
    title = "Skills"
    description = "Skills, upgrades and points will be connected here."


class HealthTab(GameMenuTab):
    tab_id = "health"
    title = "Health"
    description = "Health, conditions and status effects will be connected here."


class QuestsTab(GameMenuTab):
    tab_id = "quests"
    title = "Quests"
    description = "Active quests and objectives will be connected here."


class MapTab(GameMenuTab):
    tab_id = "map"
    title = "Map"
    description = "The world map and markers will be connected here."


class GameTab(GameMenuTab):
    """The system-independent game actions tab."""

    tab_id = "game"
    title = "Game"
    description = "Save the game, change options or leave the game."

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(name, world)

        self._action_panel = self.create_child(
            "Actions",
            node_type=Panel,
        )
        self._action_panel.background = (
            25,
            28,
            33,
            255,
        )
        self._action_panel.border_color = (
            89,
            64,
            34,
            255,
        )
        self._action_panel.border_width = 1.0
        self._action_panel.border_radius = 4.0

        self._save_button = self._make_button(
            "SaveButton",
            "Save Game",
            self._request_save,
        )
        self._options_button = self._make_button(
            "OptionsButton",
            "Options",
            self._request_options,
        )
        self._main_menu_button = self._make_button(
            "MainMenuButton",
            "Main Menu",
            self._request_main_menu,
        )
        self._quit_button = self._make_button(
            "QuitButton",
            "Quit Game",
            self._request_quit,
        )

        self._on_save: Callback | None = None
        self._on_options: Callback | None = None
        self._on_main_menu: Callback | None = None
        self._on_quit: Callback | None = None

    def _make_button(
        self,
        name: str,
        text: str,
        callback: Callback,
    ) -> Button:
        button = self._action_panel.create_child(
            name,
            node_type=_MenuButton,
        )
        button.text = text
        button.text_scale = 1.05
        button.on_click = callback
        button.normal_background = (34, 37, 42, 255)
        button.hover_background = (53, 48, 39, 255)
        button.focus_background = (74, 57, 35, 255)
        button.pressed_background = (27, 29, 33, 255)
        button.normal_border_color = (111, 81, 41, 255)
        button.focus_border_color = (224, 161, 67, 255)
        return button

    def set_callbacks(
        self,
        *,
        on_save: Callback | None = None,
        on_options: Callback | None = None,
        on_main_menu: Callback | None = None,
        on_quit: Callback | None = None,
    ) -> None:
        """Attach game-specific actions to the four Game-tab buttons."""

        self._on_save = on_save
        self._on_options = on_options
        self._on_main_menu = on_main_menu
        self._on_quit = on_quit

    def _request_save(self) -> None:
        if self._on_save is not None:
            self._on_save()

    def _request_options(self) -> None:
        if self._on_options is not None:
            self._on_options()

    def _request_main_menu(self) -> None:
        if self._on_main_menu is not None:
            self._on_main_menu()

    def _request_quit(self) -> None:
        if self._on_quit is not None:
            self._on_quit()

    def _sync_layout(self) -> None:
        super()._sync_layout()

        width, height = self.size
        panel_width = max(260.0, width - 56.0)
        panel_height = min(280.0, max(220.0, height - 150.0))

        self._action_panel.size = (
            panel_width,
            panel_height,
        )
        self._action_panel.position = (
            0.0,
            82.0,
        )

        buttons = (
            self._save_button,
            self._options_button,
            self._main_menu_button,
            self._quit_button,
        )

        spacing = 12.0
        button_height = 46.0
        total_height = (
            len(buttons) * button_height
            + (len(buttons) - 1) * spacing
        )
        first_y = -total_height / 2.0 + button_height / 2.0

        for index, button in enumerate(buttons):
            button.size = (
                panel_width - 32.0,
                button_height,
            )
            button.position = (
                0.0,
                first_y + index * (button_height + spacing),
            )


class GameMenu(UINode):
    """Modular, pausing in-game menu.

    ``GameMenu`` owns the tab nodes directly. The eight default tabs are
    intentionally light shells so a project can grow each system separately:

    * equipment
    * inventory
    * crafting
    * skills
    * health
    * quests
    * map
    * game

    The menu reads actions from Nexora's ``InputManager``. It never imports
    SDL and never decides which physical key an action uses. The default
    physical bindings live in ``core/defaults/keybinds.toml``.
    """

    TAB_TYPES = (
        EquipmentTab,
        InventoryTab,
        CraftingTab,
        SkillsTab,
        HealthTab,
        QuestsTab,
        MapTab,
        GameTab,
    )

    def __init__(
        self,
        name: str,
        world,
    ) -> None:
        super().__init__(name, world)

        self.width_mode = "fill"
        self.height_mode = "fill"

        # The menu pauses by default. A project can turn this off for a
        # non-pausing overlay without changing the input implementation.
        self.pause_on_open = True

        # Semantic action names, not physical keys. ``pause`` already ships
        # with Nexora and is mapped in the default keybind TOML.
        self.toggle_action = "pause"
        self.back_action = "menu_back"
        self.next_tab_action = "menu_next_tab"
        self.previous_tab_action = "menu_previous_tab"
        self.confirm_action = "menu_confirm"
        self.focus_up_action = "menu_up"
        self.focus_down_action = "menu_down"
        self.focus_left_action = "menu_left"
        self.focus_right_action = "menu_right"

        self.input_manager: InputManager | None = None

        self._pause_callback: Callback | None = None
        self._resume_callback: Callback | None = None
        self._paused_by_menu = False
        self._is_open = False
        self._active_tab_id = "equipment"

        self._on_save: Callback | None = None
        self._on_options: Callback | None = None
        self._on_main_menu: Callback | None = None
        self._on_quit: Callback | None = None

        self.opened = Signal(
            f"{name}.opened",
            owner=self,
        )
        self.closed = Signal(
            f"{name}.closed",
            owner=self,
        )
        self.tab_changed = Signal(
            f"{name}.tab_changed",
            owner=self,
        )
        self.save_requested = Signal(
            f"{name}.save_requested",
            owner=self,
        )
        self.options_requested = Signal(
            f"{name}.options_requested",
            owner=self,
        )
        self.main_menu_requested = Signal(
            f"{name}.main_menu_requested",
            owner=self,
        )
        self.quit_requested = Signal(
            f"{name}.quit_requested",
            owner=self,
        )

        self._backdrop = self.create_child(
            "Backdrop",
            node_type=Panel,
        )
        self._backdrop.background = (
            4,
            7,
            12,
            220,
        )

        self._window = self.create_child(
            "Window",
            node_type=Panel,
        )
        self._window.background = (
            16,
            19,
            24,
            255,
        )
        self._window.border_color = (
            180,
            122,
            48,
            255,
        )
        self._window.border_width = 2.0
        self._window.border_radius = 6.0

        self._header = self._window.create_child(
            "Header",
            node_type=Panel,
        )
        self._header.background = (
            28,
            27,
            29,
            255,
        )
        self._header.border_color = (
            101,
            72,
            38,
            255,
        )
        self._header.border_width = 1.0

        self._header_label = self._header.create_child(
            "HeaderLabel",
            node_type=Label,
        )
        self._header_label.text = "GAME MENU"
        self._header_label.scale = 1.35
        self._header_label.anchor = (0.5, 0.5)
        self._header_label.pivot = (0.0, 0.5)

        self._sidebar = self._window.create_child(
            "Tabs",
            node_type=Panel,
        )
        self._sidebar.background = (
            12,
            15,
            19,
            255,
        )
        self._sidebar.border_color = (
            82,
            60,
            35,
            255,
        )
        self._sidebar.border_width = 1.0
        self._sidebar.border_radius = 4.0

        self._content_frame = self._window.create_child(
            "ContentFrame",
            node_type=Panel,
        )
        self._content_frame.background = (
            20,
            23,
            28,
            255,
        )
        self._content_frame.border_color = (
            82,
            60,
            35,
            255,
        )
        self._content_frame.border_width = 1.0
        self._content_frame.border_radius = 4.0

        self._tab_buttons: dict[str, Button] = {}
        self._tabs: dict[str, GameMenuTab] = {}

        for tab_type in self.TAB_TYPES:
            tab = self.create_child(
                f"{tab_type.tab_id.title()}Tab",
                node_type=tab_type,
            )
            self._tabs[tab.tab_id] = tab

            button = self._sidebar.create_child(
                f"{tab.tab_id.title()}Button",
                node_type=_MenuButton,
            )
            button.text = tab.title
            button.text_scale = 0.95
            button.on_click = (
                lambda tab_id=tab.tab_id: self.set_active_tab(tab_id)
            )
            button.normal_background = (29, 32, 37, 255)
            button.hover_background = (49, 45, 38, 255)
            button.focus_background = (74, 57, 35, 255)
            button.pressed_background = (24, 26, 30, 255)
            button.normal_border_color = (78, 78, 78, 255)
            button.focus_border_color = (224, 161, 67, 255)
            self._tab_buttons[tab.tab_id] = button

        game_tab = self._tabs[GameTab.tab_id]
        if isinstance(game_tab, GameTab):
            game_tab.set_callbacks(
                on_save=self._request_save,
                on_options=self._request_options,
                on_main_menu=self._request_main_menu,
                on_quit=self._request_quit,
            )

        self._set_active_tab(
            self._active_tab_id,
            focus=False,
        )

        self.visible = False

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def active_tab_id(self) -> str:
        return self._active_tab_id

    @property
    def tabs(self) -> dict[str, GameMenuTab]:
        """Return the menu's tab nodes by stable id."""

        return self._tabs

    def tab(self, tab_id: str) -> GameMenuTab:
        """Return one tab so a project can extend its content."""

        try:
            return self._tabs[str(tab_id)]
        except KeyError as exc:
            raise KeyError(f"Unknown GameMenu tab: {tab_id}") from exc

    def set_input_manager(
        self,
        input_manager: InputManager | None,
    ) -> None:
        self.input_manager = input_manager

    def set_pause_handlers(
        self,
        *,
        pause: Callback | None = None,
        resume: Callback | None = None,
    ) -> None:
        """Set the callbacks used when the menu pauses or resumes gameplay."""

        self._pause_callback = pause
        self._resume_callback = resume

    def set_game_callbacks(
        self,
        *,
        on_save: Callback | None = None,
        on_options: Callback | None = None,
        on_main_menu: Callback | None = None,
        on_quit: Callback | None = None,
    ) -> None:
        self._on_save = on_save
        self._on_options = on_options
        self._on_main_menu = on_main_menu
        self._on_quit = on_quit

        game_tab = self._tabs[GameTab.tab_id]
        if isinstance(game_tab, GameTab):
            game_tab.set_callbacks(
                on_save=self._request_save,
                on_options=self._request_options,
                on_main_menu=self._request_main_menu,
                on_quit=self._request_quit,
            )

    def open(self) -> None:
        if self._is_open:
            return

        self._is_open = True
        self.visible = True

        if self.pause_on_open and self._pause_callback is not None:
            self._pause_callback()
            self._paused_by_menu = True

        root = self.ui_root
        if root is not None:
            root.push_modal(self)

        self._focus_active_tab_button()
        self.opened.emit()

    def close(self) -> None:
        if not self._is_open:
            return

        root = self.ui_root
        if root is not None:
            root.pop_modal(self)

        self._is_open = False
        self.visible = False

        if self._paused_by_menu and self._resume_callback is not None:
            self._resume_callback()

        self._paused_by_menu = False
        self.closed.emit()

    def toggle(self) -> None:
        if self._is_open:
            self.close()
        else:
            self.open()

    def set_active_tab(
        self,
        tab_id: str,
    ) -> None:
        self._set_active_tab(str(tab_id), focus=True)

    def _set_active_tab(
        self,
        tab_id: str,
        *,
        focus: bool,
    ) -> None:
        if tab_id not in self._tabs:
            raise KeyError(f"Unknown GameMenu tab: {tab_id}")

        previous = self._active_tab_id
        self._active_tab_id = tab_id

        for current_id, tab in self._tabs.items():
            tab.visible = current_id == tab_id

            button = self._tab_buttons[current_id]
            if current_id == tab_id:
                button.normal_background = (69, 53, 34, 255)
            else:
                button.normal_background = (29, 32, 37, 255)

        if focus:
            self._focus_active_tab_button()

        if previous != tab_id:
            self.tab_changed.emit(tab_id, previous)

    def _focus_active_tab_button(self) -> None:
        if not self._is_open:
            return

        button = self._tab_buttons.get(self._active_tab_id)
        if button is not None:
            button.focus()

    def select_next_tab(self) -> None:
        tab_ids = tuple(self._tabs)
        index = tab_ids.index(self._active_tab_id)
        self.set_active_tab(tab_ids[(index + 1) % len(tab_ids)])

    def select_previous_tab(self) -> None:
        tab_ids = tuple(self._tabs)
        index = tab_ids.index(self._active_tab_id)
        self.set_active_tab(tab_ids[(index - 1) % len(tab_ids)])

    def _focus_menu_node(self, direction: int) -> None:
        root = self.ui_root
        if root is None:
            return

        nodes = root._collect_focusable_nodes(self)
        if not nodes:
            return

        current = root.focused_node
        if current not in nodes:
            root.set_focus(nodes[0 if direction > 0 else -1])
            return

        index = nodes.index(current)
        root.set_focus(nodes[(index + direction) % len(nodes)])

    def _confirm_focused_menu_node(self) -> None:
        root = self.ui_root
        if root is None:
            return

        focused = root.focused_node
        if isinstance(focused, _MenuButton):
            focused.click()

    def _action_pressed(self, action: str) -> bool:
        if self.input_manager is None:
            return False

        return bool(
            self.input_manager.is_action_pressed(action)
        )

    def update(self, delta_time: float) -> None:
        del delta_time

        if self.input_manager is None:
            return

        toggle_pressed = self._action_pressed(self.toggle_action)

        if not self._is_open:
            if toggle_pressed:
                self.open()
            return

        if toggle_pressed or self._action_pressed(self.back_action):
            self.close()
            return

        if self._action_pressed(self.next_tab_action):
            self.select_next_tab()
        elif self._action_pressed(self.previous_tab_action):
            self.select_previous_tab()

        if self._action_pressed(self.focus_down_action):
            self._focus_menu_node(1)
        elif self._action_pressed(self.focus_up_action):
            self._focus_menu_node(-1)

        if self._action_pressed(self.focus_right_action):
            self.select_next_tab()
        elif self._action_pressed(self.focus_left_action):
            self.select_previous_tab()

        if self._action_pressed(self.confirm_action):
            self._confirm_focused_menu_node()

    def update_input(self, ui_input) -> None:
        if not self._is_open:
            self.reset_interaction_state()
            return

        self._sync_layout()
        super().update_input(ui_input)

    def render(self, renderer) -> None:
        if not self.visible:
            return

        self._sync_layout()
        super().render(renderer)

    def _sync_layout(self) -> None:
        viewport_width = max(1.0, self.size[0])
        viewport_height = max(1.0, self.size[1])

        self._backdrop.size = (
            viewport_width,
            viewport_height,
        )
        self._backdrop.position = (0.0, 0.0)

        window_width = min(1080.0, viewport_width - 48.0)
        window_height = min(660.0, viewport_height - 48.0)
        window_width = max(640.0, window_width)
        window_height = max(420.0, window_height)

        self._window.size = (
            window_width,
            window_height,
        )
        self._window.position = (0.0, 0.0)

        header_height = 64.0
        self._header.size = (
            window_width,
            header_height,
        )
        self._header.position = (
            0.0,
            -window_height / 2.0 + header_height / 2.0,
        )
        self._header_label.position = (
            -window_width / 2.0 + 28.0,
            0.0,
        )

        sidebar_width = 220.0
        body_height = window_height - header_height - 24.0
        body_y = header_height / 2.0 + 6.0

        self._sidebar.size = (
            sidebar_width,
            body_height,
        )
        self._sidebar.position = (
            -window_width / 2.0 + sidebar_width / 2.0 + 16.0,
            body_y,
        )

        content_width = window_width - sidebar_width - 48.0
        content_height = body_height
        content_x = (
            -window_width / 2.0
            + sidebar_width
            + 32.0
            + content_width / 2.0
        )

        self._content_frame.size = (
            content_width,
            content_height,
        )
        self._content_frame.position = (
            content_x,
            body_y,
        )

        tab_ids = tuple(self._tabs)
        button_height = 43.0
        button_spacing = 8.0
        first_y = (
            -body_height / 2.0
            + 34.0
            + button_height / 2.0
        )

        for index, tab_id in enumerate(tab_ids):
            button = self._tab_buttons[tab_id]
            button.size = (
                sidebar_width - 24.0,
                button_height,
            )
            button.position = (
                0.0,
                first_y + index * (button_height + button_spacing),
            )

        tab_width = max(1.0, content_width - 16.0)
        tab_height = max(1.0, content_height - 16.0)

        for tab in self._tabs.values():
            tab.size = (
                tab_width,
                tab_height,
            )
            tab.position = (
                content_x,
                body_y,
            )

    def _request_save(self) -> None:
        self.save_requested.emit()
        if self._on_save is not None:
            self._on_save()

    def _request_options(self) -> None:
        self.options_requested.emit()
        if self._on_options is not None:
            self._on_options()

    def _request_main_menu(self) -> None:
        self.close()
        self.main_menu_requested.emit()
        if self._on_main_menu is not None:
            self._on_main_menu()

    def _request_quit(self) -> None:
        self.close()
        self.quit_requested.emit()
        if self._on_quit is not None:
            self._on_quit()
