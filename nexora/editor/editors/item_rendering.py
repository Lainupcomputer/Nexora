from __future__ import annotations

from nexora.editor.ui import (
    FormLayout, Rect, centered_rect, draw_outline, draw_rect, draw_text,
    layout_equal_row,
    layout_fixed_row, render_document_title, render_editor_shell,
    render_form_label, render_section_title, render_status_bar,
)


class ItemRenderingMixin:

    def _layout(self) -> tuple[float, float]:
        width = float(self.game.renderer.width)
        height = float(self.game.renderer.height)
        if (width, height) == self._layout_size:
            return width, height
        self._layout_size = (width, height)
        body_top = self.TOOLBAR_HEIGHT
        body_bottom = height - self.STATUS_HEIGHT
        body_height = max(0.0, body_bottom - body_top)
        left = min(self.LEFT_WIDTH, width * 0.25)
        preview = min(self.PREVIEW_WIDTH, max(260.0, width * 0.24))
        self.left_panel = Rect(0.0, body_top, left, body_height)
        self.preview_panel = Rect(left, body_top, preview, body_height)
        self.form_panel = Rect(left + preview, body_top, max(0.0, width - left - preview), body_height)
        self._layout_controls(width, height)
        return width, height

    def _layout_controls(self, width: float, height: float) -> None:
        layout_fixed_row(
            (self.file_menu, self.item_menu, self.help_menu),
            (82.0, 88.0, 86.0),
            x=105.0,
            y=5.0,
            height=38.0,
            gap=(7.0, 23.0),
        )
        self.item_search.rect = Rect(self.left_panel.x + 12.0, self.left_panel.y + 46.0, self.left_panel.width - 24.0, 34.0)
        self.item_list.rect = Rect(self.left_panel.x + 12.0, self.left_panel.y + 88.0, self.left_panel.width - 24.0, max(120.0, self.left_panel.height - 152.0))
        button_y = self.left_panel.y + self.left_panel.height - 52.0
        layout_equal_row(
            (self.new_button, self.open_button, self.save_button),
            x=self.left_panel.x + 12.0,
            y=button_y,
            width=self.left_panel.width - 24.0,
            height=32.0,
            gap=6.0,
        )

        self.icon_preview = Rect(self.preview_panel.x + 36.0, self.preview_panel.y + 74.0, min(self.preview_panel.width - 72.0, 248.0), min(self.preview_panel.width - 72.0, 248.0))
        self.icon_button.rect = Rect(self.preview_panel.x + 36.0, self.icon_preview.y + self.icon_preview.height + 18.0, self.icon_preview.width, 34.0)

        x = self.form_panel.x + 16.0
        inner = max(240.0, self.form_panel.width - 32.0)
        content_top = self.form_panel.y + 118.0
        form = FormLayout(
            x=x,
            y=content_top,
            width=inner,
            columns=2,
            column_gap=10.0,
            row_step=52.0,
            control_height=34.0,
            label_gap=18.0,
        )
        half = max(110.0, form.column_width)
        right = x + half + form.column_gap
        field_height = form.control_height
        row = form.row_step
        self._tab_layouts = {
            "General": [
                ("Item ID", "id", x, content_top, half),
                ("Display Name", "name", right, content_top, half),
                ("Description", "description", x, content_top + row, inner),
                ("Tags (comma separated)", "tags", x, content_top + row * 2.0, inner),
                ("Icon Asset", "icon", x, content_top + row * 3.0, half),
                ("World Sprite", "world_sprite", right, content_top + row * 3.0, half),
                ("Drop Sprite", "drop_sprite", x, content_top + row * 4.0, half),
                ("Author", "author", right, content_top + row * 4.0, half),
                ("GUID", "guid", x, content_top + row * 5.0, half),
                ("Editor Notes", "notes", right, content_top + row * 5.0, half),
            ],
            "Gameplay": [
                ("Max Stack", "max_stack", x, content_top, half),
                ("Value", "value", right, content_top, half),
                ("Weight", "weight", x, content_top + row, half),
                ("Equip Slot", "equip_slot", right, content_top + row, half),
                ("Durability", "durability", x, content_top + row * 2.0, half),
                ("Armor Defense", "armor_defense", right, content_top + row * 2.0, half),
                ("Armor Resistance", "armor_resistance", x, content_top + row * 3.0, half),
                ("Weapon Damage", "weapon_damage", right, content_top + row * 3.0, half),
                ("Attack Speed", "weapon_speed", x, content_top + row * 4.0, half),
                ("Weapon Range", "weapon_range", right, content_top + row * 4.0, half),
                ("Tool Type", "tool_type", x, content_top + row * 5.0, half),
                ("Tool Power", "tool_power", right, content_top + row * 5.0, half),
                ("Health Bonus", "bonus_health", x, content_top + row * 6.0, half),
                ("Stamina Bonus", "bonus_stamina", right, content_top + row * 6.0, half),
                ("Mana Bonus", "bonus_mana", x, content_top + row * 7.0, half),
                ("Move Speed Bonus", "bonus_move_speed", right, content_top + row * 7.0, half),
                ("Sprint Multiplier", "bonus_sprint", x, content_top + row * 8.0, half),
                ("Sneak Multiplier", "bonus_sneak", right, content_top + row * 8.0, half),
            ],
            "Use": [
                ("Cooldown (seconds)", "use_cooldown", x, content_top + row, half),
                ("Use Animation", "use_animation", right, content_top + row, half),
                ("Pickup Sound", "pickup_sound", x, content_top + row * 2.0, half),
                ("Use Sound", "use_sound", right, content_top + row * 2.0, half),
                ("Equip Sound", "equip_sound", x, content_top + row * 3.0, half),
                ("Drop Sound", "drop_sound", right, content_top + row * 3.0, half),
                ("Use Callback ID", "use_callback", x, content_top + row * 4.0, half),
                ("Equip Callback ID", "equip_callback", right, content_top + row * 4.0, half),
                ("Drop Callback ID", "drop_callback", x, content_top + row * 5.0, half),
            ],
            "Effects": [],
            "Crafting": [
                ("Crafting Station", "crafting_station", x, content_top, half),
                ("Crafting Time (seconds)", "crafting_time", right, content_top, half),
                ("Output Count", "crafting_output", x, content_top + row, half),
            ],
            "Loot": [
                ("Minimum Quantity", "loot_min", x, content_top, half),
                ("Maximum Quantity", "loot_max", right, content_top, half),
                ("Drop Chance (0-1)", "loot_chance", x, content_top + row, half),
                ("Drop Weight", "loot_weight", right, content_top + row, half),
                ("Drop Source", "loot_source", x, content_top + row * 2.0, inner),
                ("Required Level", "req_level", x, content_top + row * 3.0, half),
                ("Required Skill", "req_skill", right, content_top + row * 3.0, half),
                ("Required Skill Level", "req_skill_level", x, content_top + row * 4.0, half),
                ("Loot Table", "loot_table", x, content_top + row * 5.0, half),
                ("Drop Conditions", "loot_conditions", right, content_top + row * 5.0, half),
            ],
            "Shop": [
                ("Buy Price", "shop_buy", x, content_top, half),
                ("Sell Price", "shop_sell", right, content_top, half),
                ("Stock (-1 = unlimited)", "shop_stock", x, content_top + row, half),
                ("Vendor Category", "shop_vendor", right, content_top + row, half),
                ("Unlock Level", "shop_unlock_level", x, content_top + row * 2.0, half),
                ("Currency", "shop_currency", right, content_top + row * 2.0, half),
            ],
        }
        for index in range(1, self.effect_capacity + 1):
            base_y = content_top + index * 70.0
            self._tab_layouts["Effects"].extend([
                (f"Effect {index} Type", f"effect_{index}_type", x, base_y, half),
                ("Value", f"effect_{index}_value", right, base_y, half),
                ("Duration", f"effect_{index}_duration", x, base_y + 52.0, half),
                ("Status", f"effect_{index}_status", right, base_y + 52.0, half),
            ])
        for index in range(1, self.ingredient_capacity + 1):
            base_y = content_top + 122.0 + (index - 1) * 52.0
            self._tab_layouts["Crafting"].extend([
                (f"Ingredient {index}", f"ingredient_{index}", x, base_y, half),
                ("Count", f"ingredient_{index}_count", right, base_y, half),
            ])
        for specs in self._tab_layouts.values():
            for _label, name, field_x, label_y, field_width in specs:
                self.fields[name].rect = Rect(field_x, label_y + 18.0, field_width, field_height)

        tab_x = self.form_panel.x + 166.0
        tab_y = self.form_panel.y + 10.0
        columns = 4
        tab_width = min(112.0, max(78.0, (self.form_panel.width - 182.0) / columns))
        for index, button in enumerate(self.tab_buttons):
            column = index % columns
            row_index = index // columns
            button.rect = Rect(tab_x + column * (tab_width + 6.0), tab_y + row_index * 38.0, tab_width, 34.0)
            button.selected = button.text == self.active_tab

        self.category.rect = Rect(x, content_top + row * 6.0, half, field_height)
        self.rarity.rect = Rect(right, content_top + row * 6.0, half, field_height)
        self.usable.rect = Rect(x, content_top + row * 9.0, 130.0, 30.0)
        self.equippable.rect = Rect(x + 142.0, content_top + row * 9.0, 150.0, 30.0)
        self.can_buy.rect = Rect(x, content_top + row * 4.0, 120.0, 30.0)
        self.can_sell.rect = Rect(x + 132.0, content_top + row * 4.0, 120.0, 30.0)
        self.use_action.rect = Rect(x, content_top, half, field_height)
        self.use_target.rect = Rect(right, content_top, half, field_height)

        self._layout_modal_controls(width, height)

    def _layout_modal_controls(self, width: float, height: float) -> None:
        self._layout_file_dialog((width, height))
        info_window = centered_rect((width, height), 660.0, 340.0)
        self.info_close_button.rect = Rect(info_window.x + info_window.width - 126.0, info_window.y + info_window.height - 52.0, 108.0, 32.0)

    def _render_form(self, renderer, viewport_size: tuple[float, float]) -> None:
        for label, name, field_x, label_y, _field_width in self._tab_layouts.get(self.active_tab, ()):
            render_form_label(renderer, viewport_size, self.theme, label, field_x, label_y)
            self.fields[name].render(renderer, viewport_size, self.theme)
        if self.active_tab == "General":
            render_form_label(renderer, viewport_size, self.theme, "Category", self.category.rect.x, self.category.rect.y - 18.0)
            self.category.render(renderer, viewport_size, self.theme)
            render_form_label(renderer, viewport_size, self.theme, "Rarity", self.rarity.rect.x, self.rarity.rect.y - 18.0)
            self.rarity.render(renderer, viewport_size, self.theme)
        elif self.active_tab == "Gameplay":
            self.usable.render(renderer, viewport_size, self.theme)
            self.equippable.render(renderer, viewport_size, self.theme)
        elif self.active_tab == "Use":
            render_form_label(renderer, viewport_size, self.theme, "Use Action", self.use_action.rect.x, self.use_action.rect.y - 18.0)
            self.use_action.render(renderer, viewport_size, self.theme)
            render_form_label(renderer, viewport_size, self.theme, "Target", self.use_target.rect.x, self.use_target.rect.y - 18.0)
            self.use_target.render(renderer, viewport_size, self.theme)
        elif self.active_tab == "Shop":
            self.can_buy.render(renderer, viewport_size, self.theme)
            self.can_sell.render(renderer, viewport_size, self.theme)

    def _render_main(self, renderer, viewport_size: tuple[float, float]) -> None:
        width, height = viewport_size
        render_editor_shell(
            renderer,
            viewport_size,
            self.theme,
            toolbar_height=self.TOOLBAR_HEIGHT,
            status_height=self.STATUS_HEIGHT,
            panels=(
                (self.left_panel, self.theme.panel),
                (self.preview_panel, self.theme.panel_dark),
                (self.form_panel, self.theme.panel),
            ),
            outline_rects=(self.left_panel, self.preview_panel, self.form_panel),
        )
        render_document_title(
            renderer,
            viewport_size,
            self.theme,
            self.item.name,
            dirty=self.dirty,
            scale=0.62,
        )
        render_section_title(renderer, viewport_size, self.theme, self.left_panel, "Items")
        render_section_title(
            renderer,
            viewport_size,
            self.theme,
            self.preview_panel,
            "Preview",
            x_offset=16.0,
        )
        render_section_title(
            renderer,
            viewport_size,
            self.theme,
            self.form_panel,
            "Item Properties",
            x_offset=16.0,
        )
        render_status_bar(
            renderer,
            viewport_size,
            self.theme,
            self.status,
            "Nexora Item Editor",
            status_height=self.STATUS_HEIGHT,
        )

        self.item_search.render(renderer, viewport_size, self.theme)
        self.item_list.render(renderer, viewport_size, self.theme)
        for button in (self.new_button, self.open_button, self.save_button):
            button.render(renderer, viewport_size, self.theme)
        for menu in self.menus:
            menu.render(renderer, viewport_size, self.theme)
        for button in self.tab_buttons:
            button.render(renderer, viewport_size, self.theme)

        draw_rect(renderer, self.icon_preview, self.theme.input, viewport_size, radius=5.0)
        draw_outline(renderer, self.icon_preview, self.theme.border, viewport_size)
        if self.icon_texture is not None:
            center_x, center_y = self.icon_preview.center()
            sprite_x = center_x - width / 2.0
            sprite_y = center_y - height / 2.0
            size = min(self.icon_preview.width - 28.0, self.icon_preview.height - 28.0)
            renderer.sprite(self.icon_texture, sprite_x, sprite_y, width=size, height=size)
        else:
            draw_text(renderer, "No icon", *self.icon_preview.center(), viewport_size, scale=0.62, color=self.theme.muted, align="center")
        self.icon_button.render(renderer, viewport_size, self.theme)
        self._render_form(renderer, viewport_size)

    def _render_browser(self, renderer, viewport_size: tuple[float, float]) -> None:
        title = {
            "open": "Open Item",
            "save": "Save Item As",
            "icon": "Choose Item Icon",
        }[self.browser_mode]
        self._render_file_dialog(renderer, viewport_size, title=title)

