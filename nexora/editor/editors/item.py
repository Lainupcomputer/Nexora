from __future__ import annotations

"""Standalone editor for Nexora ``.nitem`` resources."""

from pathlib import Path

from nexora.editor.base_editor import EditorBaseScene
from nexora.editor.model import EditorProjectContext
from nexora.editor.standalone_app import StandaloneEditorApp, run_standalone_editor
from nexora.editor.editors.item_assets import ItemAssetsMixin
from nexora.editor.editors.item_catalog import ItemCatalogMixin
from nexora.editor.editors.item_document import ItemDocumentMixin
from nexora.editor.editors.item_rendering import ItemRenderingMixin
from nexora.editor.ui import (
    Button,
    CategorizedListBox,
    CheckBox,
    Dropdown,
    Menu,
    Rect,
    TextField,
    draw_rect,
)
from nexora.gameplay.items import ItemDefinition



class ItemEditorScene(
    ItemDocumentMixin,
    ItemCatalogMixin,
    ItemAssetsMixin,
    ItemRenderingMixin,
    EditorBaseScene,
):
    """Renderer-backed item authoring scene with a custom standalone UI."""

    TOOLBAR_HEIGHT = EditorBaseScene.TOOLBAR_HEIGHT
    STATUS_HEIGHT = EditorBaseScene.STATUS_HEIGHT
    LEFT_WIDTH = 300.0
    PREVIEW_WIDTH = 320.0
    CONTROL_STOP_ON_HANDLED = True
    CONTROL_MANAGE_TEXT_FOCUS = False

    def __init__(
        self,
        game,
        project_path: Path,
        item_path: str | Path | None = None,
        project_context: EditorProjectContext | None = None,
    ) -> None:
        super().__init__("StandaloneItemEditor")
        self.game = game
        self.project_context = project_context or EditorProjectContext.from_path(project_path)
        self.project_path = self.project_context.root
        self.assets_root = self.project_context.assets_root
        self.items_root = self.project_context.items_root
        self.item = ItemDefinition()
        self.document_path: Path | None = None
        self.dirty = False
        self.status = "Ready"
        self.browser_mode = "open"
        self.browser_root = self.project_path
        self.browser_path = self._item_start_path()
        self.icon_texture = None
        self._layout_size = (-1.0, -1.0)
        self._loading = False
        self.active_tab = "General"
        self.tab_names = ("General", "Gameplay", "Use", "Effects", "Crafting", "Loot", "Shop")
        self.effect_capacity = 4
        self.ingredient_capacity = 6
        self._tab_layouts: dict[str, list[tuple[str, str, float, float, float]]] = {}

        self.fields = {
            "id": TextField(Rect(0, 0, 1, 1), "new_item"),
            "name": TextField(Rect(0, 0, 1, 1), "New Item"),
            "description": TextField(Rect(0, 0, 1, 1), ""),
            "max_stack": TextField(Rect(0, 0, 1, 1), "1"),
            "value": TextField(Rect(0, 0, 1, 1), "0"),
            "weight": TextField(Rect(0, 0, 1, 1), "0.0"),
            "equip_slot": TextField(Rect(0, 0, 1, 1), "none"),
            "tags": TextField(Rect(0, 0, 1, 1), ""),
            "icon": TextField(Rect(0, 0, 1, 1), ""),
            "weapon_damage": TextField(Rect(0, 0, 1, 1), "0"),
            "weapon_speed": TextField(Rect(0, 0, 1, 1), "1.0"),
            "weapon_range": TextField(Rect(0, 0, 1, 1), "1.0"),
            "tool_type": TextField(Rect(0, 0, 1, 1), ""),
            "tool_power": TextField(Rect(0, 0, 1, 1), "0"),
            "durability": TextField(Rect(0, 0, 1, 1), "0"),
            "armor_defense": TextField(Rect(0, 0, 1, 1), "0"),
            "armor_resistance": TextField(Rect(0, 0, 1, 1), "0"),
            "consumable_health": TextField(Rect(0, 0, 1, 1), "0"),
            "consumable_stamina": TextField(Rect(0, 0, 1, 1), "0"),
            "consumable_mana": TextField(Rect(0, 0, 1, 1), "0"),
            "effect_type": TextField(Rect(0, 0, 1, 1), ""),
            "effect_value": TextField(Rect(0, 0, 1, 1), "0"),
            "effect_duration": TextField(Rect(0, 0, 1, 1), "0"),
            "effect_status": TextField(Rect(0, 0, 1, 1), ""),
            "crafting_station": TextField(Rect(0, 0, 1, 1), ""),
            "crafting_time": TextField(Rect(0, 0, 1, 1), "0"),
            "crafting_output": TextField(Rect(0, 0, 1, 1), "1"),
            "ingredient_1": TextField(Rect(0, 0, 1, 1), ""),
            "ingredient_1_count": TextField(Rect(0, 0, 1, 1), "1"),
            "ingredient_2": TextField(Rect(0, 0, 1, 1), ""),
            "ingredient_2_count": TextField(Rect(0, 0, 1, 1), "1"),
            "loot_min": TextField(Rect(0, 0, 1, 1), "1"),
            "loot_max": TextField(Rect(0, 0, 1, 1), "1"),
            "loot_chance": TextField(Rect(0, 0, 1, 1), "1.0"),
            "loot_weight": TextField(Rect(0, 0, 1, 1), "1.0"),
            "loot_source": TextField(Rect(0, 0, 1, 1), ""),
            "loot_table": TextField(Rect(0, 0, 1, 1), ""),
            "loot_conditions": TextField(Rect(0, 0, 1, 1), ""),
            "req_level": TextField(Rect(0, 0, 1, 1), "0"),
            "req_skill": TextField(Rect(0, 0, 1, 1), ""),
            "req_skill_level": TextField(Rect(0, 0, 1, 1), "0"),
            "world_sprite": TextField(Rect(0, 0, 1, 1), ""),
            "drop_sprite": TextField(Rect(0, 0, 1, 1), ""),
            "author": TextField(Rect(0, 0, 1, 1), ""),
            "guid": TextField(Rect(0, 0, 1, 1), ""),
            "notes": TextField(Rect(0, 0, 1, 1), ""),
            "use_cooldown": TextField(Rect(0, 0, 1, 1), "0"),
            "use_animation": TextField(Rect(0, 0, 1, 1), ""),
            "use_callback": TextField(Rect(0, 0, 1, 1), ""),
            "equip_callback": TextField(Rect(0, 0, 1, 1), ""),
            "drop_callback": TextField(Rect(0, 0, 1, 1), ""),
            "pickup_sound": TextField(Rect(0, 0, 1, 1), ""),
            "use_sound": TextField(Rect(0, 0, 1, 1), ""),
            "equip_sound": TextField(Rect(0, 0, 1, 1), ""),
            "drop_sound": TextField(Rect(0, 0, 1, 1), ""),
            "bonus_health": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_stamina": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_mana": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_move_speed": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_sprint": TextField(Rect(0, 0, 1, 1), "0"),
            "bonus_sneak": TextField(Rect(0, 0, 1, 1), "0"),
            "shop_buy": TextField(Rect(0, 0, 1, 1), "0"),
            "shop_sell": TextField(Rect(0, 0, 1, 1), "0"),
            "shop_stock": TextField(Rect(0, 0, 1, 1), "-1"),
            "shop_vendor": TextField(Rect(0, 0, 1, 1), ""),
            "shop_unlock_level": TextField(Rect(0, 0, 1, 1), "0"),
            "shop_currency": TextField(Rect(0, 0, 1, 1), "gold"),
        }
        for index in range(1, self.effect_capacity + 1):
            self.fields.update({
                f"effect_{index}_type": TextField(Rect(0, 0, 1, 1), ""),
                f"effect_{index}_value": TextField(Rect(0, 0, 1, 1), "0"),
                f"effect_{index}_duration": TextField(Rect(0, 0, 1, 1), "0"),
                f"effect_{index}_status": TextField(Rect(0, 0, 1, 1), ""),
            })
        for index in range(3, self.ingredient_capacity + 1):
            self.fields.update({
                f"ingredient_{index}": TextField(Rect(0, 0, 1, 1), ""),
                f"ingredient_{index}_count": TextField(Rect(0, 0, 1, 1), "1"),
            })
        for field in self.fields.values():
            field.on_change = self._field_changed

        self.category = Dropdown(Rect(0, 0, 1, 1), ("Misc", "Weapon", "Tool", "Armor", "Consumable", "Material", "Quest"), on_change=self._dropdown_changed)
        self.rarity = Dropdown(Rect(0, 0, 1, 1), ("Common", "Uncommon", "Rare", "Epic", "Legendary"), on_change=self._dropdown_changed)
        self.usable = CheckBox(Rect(0, 0, 1, 1), "Usable", False, self._check_changed)
        self.equippable = CheckBox(Rect(0, 0, 1, 1), "Equippable", False, self._check_changed)
        self.can_buy = CheckBox(Rect(0, 0, 1, 1), "Can Buy", True, self._check_changed)
        self.can_sell = CheckBox(Rect(0, 0, 1, 1), "Can Sell", True, self._check_changed)
        self.use_action = Dropdown(Rect(0, 0, 1, 1), ("None", "Consume", "Equip", "Throw", "Place", "Open", "Interact"), on_change=self._dropdown_changed)
        self.use_target = Dropdown(Rect(0, 0, 1, 1), ("Self", "Target", "Area", "Inventory"), on_change=self._dropdown_changed)

        self.tab_buttons = []
        for tab_name in self.tab_names:
            button = Button(Rect(0, 0, 1, 1), tab_name, lambda tab=tab_name: self._set_tab(tab))
            button.text_scale = 0.54
            self.tab_buttons.append(button)

        self.item_search = TextField(Rect(0, 0, 1, 1), "", "Search items...")
        self.item_search.on_change = self._item_search_changed
        self.item_list = CategorizedListBox(Rect(0, 0, 1, 1), self._item_selected)
        self.new_button = Button(Rect(0, 0, 1, 1), "New", self.new_item)
        self.open_button = Button(Rect(0, 0, 1, 1), "Open", lambda: self._open_browser("open"))
        self.save_button = Button(Rect(0, 0, 1, 1), "Save", self.save_item)
        self.icon_button = Button(Rect(0, 0, 1, 1), "Choose Icon", lambda: self._open_browser("icon"))
        self.info_close_button = Button(Rect(0, 0, 1, 1), "Close", self._close_modal)

        self.file_menu = Menu(Rect(0, 0, 1, 1), "File", [
            ("New", self.new_item),
            ("Open", lambda: self._open_browser("open")),
            ("Save", self.save_item),
            ("Save As", lambda: self._open_browser("save")),
            ("Exit", self.game.stop),
        ])
        self.item_menu = Menu(Rect(0, 0, 1, 1), "Item", [
            ("Choose Icon", lambda: self._open_browser("icon")),
            ("Refresh Items", self.refresh_item_list),
            ("Validate Item", self.validate_item),
        ])
        self.help_menu = Menu(Rect(0, 0, 1, 1), "Help", [("About Item Assets", self._show_about)])
        self._set_menus([self.file_menu, self.item_menu, self.help_menu])

        self.new_item()
        self.refresh_item_list()
        if item_path is not None:
            self._load_item_path(self._resolve_requested_path(item_path))

    # ------------------------------------------------------------------
    # Project and item paths
    # ------------------------------------------------------------------



    # ------------------------------------------------------------------
    # Item state
    # ------------------------------------------------------------------

    def _set_tab(self, tab_name: str) -> None:
        if tab_name in self.tab_names:
            self.active_tab = tab_name
            for button in self.tab_buttons:
                button.selected = button.text == tab_name
            self.status = f"{tab_name} tab"













    # ------------------------------------------------------------------
    # Item browser and icon picker
    # ------------------------------------------------------------------








    # ------------------------------------------------------------------
    # UI and rendering
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        self._open_info_dialog(
            "Nexora Item Assets",
            (
                "Items are saved as versioned .nitem resources.",
                "The same data can be loaded by inventory, equipment, crafting and loot systems.",
                "Use File > Save As to create an item in the project items folder.",
            ),
        )




    def update(self, delta_time: float) -> None:
        del delta_time
        width, height = self._layout()
        mouse_x, mouse_y = self.game.input.mouse_position
        if self.modal == "browser":
            self._update_controls(self._file_dialog_controls(), mouse_x, mouse_y)
            return
        if self.modal == "info":
            self._update_controls([self.info_close_button], mouse_x, mouse_y)
            return
        menu_was_open = any(menu.open for menu in self.menus)
        self._update_controls(self.menus, mouse_x, mouse_y)
        if menu_was_open or any(menu.open for menu in self.menus):
            return
        controls = [
            self.item_search,
            self.item_list,
            self.new_button,
            self.open_button,
            self.save_button,
            self.icon_button,
            *self.tab_buttons,
        ]
        if self.active_tab == "General":
            controls.extend((self.category, self.rarity))
        elif self.active_tab == "Gameplay":
            controls.extend((self.usable, self.equippable))
        elif self.active_tab == "Use":
            controls.extend((self.use_action, self.use_target))
        elif self.active_tab == "Shop":
            controls.extend((self.can_buy, self.can_sell))
        active_fields = {name for _label, name, _x, _y, _width in self._tab_layouts.get(self.active_tab, ())}
        controls.extend(self.fields[name] for name in active_fields)
        self._update_controls(controls, mouse_x, mouse_y)
        del width, height





    def render(self, interpolation: float) -> None:
        del interpolation
        width, height = self._layout()
        renderer = self.game.renderer
        viewport_size = (width, height)
        draw_rect(renderer, Rect(0, 0, width, height), self.theme.background, viewport_size)
        with renderer.overlay_scope():
            self._render_main(renderer, viewport_size)
            if self.modal == "browser":
                self._render_browser(renderer, viewport_size)
            elif self.modal == "info":
                self._render_info_dialog(renderer, viewport_size)


class ItemEditorApp(StandaloneEditorApp[ItemEditorScene]):
    """Application wrapper for the standalone Item Editor."""

    PROJECT_NAME = "NexoraStandaloneItemEditor"
    WINDOW_TITLE = "Nexora Item Editor"
    WINDOW_WIDTH = 1440
    WINDOW_HEIGHT = 900
    ERROR_PREFIX = "Nexora Item Editor"

    def __init__(self, *, project_path: str | Path | None = None, item_path: str | Path | None = None) -> None:
        self.item_asset_path = item_path
        super().__init__(project_path=project_path)
        # Compatibility aliases retained for existing integrations/tests.
        self.item_project_path = self.project_path
        self.item_project_context = self.project_context

    def create_editor_scene(self) -> ItemEditorScene:
        return ItemEditorScene(
            self,
            self.project_path,
            self.item_asset_path,
            self.project_context,
        )


def run_item_editor(project_path: str | Path | None = None, item_path: str | Path | None = None) -> int:
    return run_standalone_editor(ItemEditorApp, project_path=project_path, item_path=item_path)


__all__ = ["ItemEditorApp", "ItemEditorScene", "run_item_editor"]
