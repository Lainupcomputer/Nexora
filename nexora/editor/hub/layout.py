from __future__ import annotations




class HubLayoutMixin:
    """Lay out Project Hub panels and tool cards."""

    def _sync_layout(self, *, force: bool = False) -> None:
        renderer = getattr(self.game, "renderer", None)
        if renderer is None:
            return

        width = float(renderer.width)
        height = float(renderer.height)
        if not force and (width, height) == self._last_viewport:
            return
        self._last_viewport = (width, height)

        self.background.size = (width, height)
        self.background.position = (0.0, 0.0)
        self.background.anchor = (0.5, 0.5)
        self.background.pivot = (0.5, 0.5)

        self.header.size = (width, self.HEADER_HEIGHT)
        self.header.anchor = (0.5, 0.0)
        self.header.pivot = (0.5, 0.0)
        self.header.position = (0.0, self.HEADER_HEIGHT / 2.0)
        self.title.position = (self.OUTER_MARGIN, -10.0)
        self.subtitle.position = (self.OUTER_MARGIN + 2.0, 22.0)
        self.header_hint.position = (-self.OUTER_MARGIN, 0.0)

        self.footer.size = (width, self.FOOTER_HEIGHT)
        self.footer.anchor = (0.5, 1.0)
        self.footer.pivot = (0.5, 1.0)
        self.footer.position = (0.0, -self.FOOTER_HEIGHT / 2.0)
        self.status_label.position = (self.OUTER_MARGIN, 0.0)
        self.close_button.size = (110.0, 34.0)
        self.close_button.anchor = (1.0, 0.5)
        self.close_button.pivot = (0.5, 0.5)
        self.close_button.position = (-self.OUTER_MARGIN - 55.0, 0.0)

        body_top = self.HEADER_HEIGHT + self.OUTER_MARGIN
        body_bottom = height - self.FOOTER_HEIGHT - self.OUTER_MARGIN
        body_height = max(360.0, body_bottom - body_top)
        left_width = min(self.LEFT_WIDTH, max(300.0, width * 0.36))
        right_width = max(
            360.0,
            width - self.OUTER_MARGIN * 2.0 - left_width - self.COLUMN_GAP,
        )

        self.project_panel.size = (left_width, body_height)
        self.project_panel.anchor = (0.0, 0.0)
        self.project_panel.pivot = (0.5, 0.5)
        self.project_panel.position = (
            self.OUTER_MARGIN + left_width / 2.0,
            body_top + body_height / 2.0,
        )

        self.tools_panel.size = (right_width, body_height)
        self.tools_panel.anchor = (0.0, 0.0)
        self.tools_panel.pivot = (0.5, 0.5)
        self.tools_panel.position = (
            self.OUTER_MARGIN + left_width + self.COLUMN_GAP + right_width / 2.0,
            body_top + body_height / 2.0,
        )

        self._sync_project_panel_layout(left_width, body_height)
        self._sync_tools_panel_layout(right_width, body_height)

    def _sync_project_panel_layout(self, width: float, height: float) -> None:
        margin = 18.0
        self.project_title.position = (margin, 16.0)
        self.project_name.position = (margin, 50.0)
        self.project_path_label.position = (margin, 80.0)

        gap = 8.0
        button_y = 126.0
        button_width = max(120.0, (width - margin * 2.0 - gap) / 2.0)
        for index, button in enumerate((self.new_project_button, self.open_project_button)):
            button.size = (button_width, 38.0)
            button.anchor = (0.0, 0.0)
            button.pivot = (0.5, 0.5)
            button.position = (
                margin + button_width / 2.0 + index * (button_width + gap),
                button_y,
            )

        self.recent_title.position = (margin, 168.0)
        list_top = 202.0
        actions_height = 78.0
        list_height = max(100.0, height - list_top - actions_height)
        self.recent_list.size = (max(120.0, width - margin * 2.0), list_height)
        self.recent_list.anchor = (0.0, 0.0)
        self.recent_list.pivot = (0.5, 0.5)
        self.recent_list.position = (
            width / 2.0,
            list_top + list_height / 2.0,
        )

        action_y = list_top + list_height + 24.0
        open_width = 132.0
        remove_width = 92.0
        self.recent_open_button.size = (open_width, 32.0)
        self.recent_open_button.anchor = (0.0, 0.0)
        self.recent_open_button.pivot = (0.5, 0.5)
        self.recent_open_button.position = (margin + open_width / 2.0, action_y)
        self.recent_remove_button.size = (remove_width, 32.0)
        self.recent_remove_button.anchor = (0.0, 0.0)
        self.recent_remove_button.pivot = (0.5, 0.5)
        self.recent_remove_button.position = (
            margin + open_width + 8.0 + remove_width / 2.0,
            action_y,
        )
        self.recent_hint.position = (margin, -10.0)

    def _layout_tool_card(
        self,
        card: Panel,
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        compact: bool = False,
    ) -> None:
        card.size = (width, height)
        card.anchor = (0.0, 0.0)
        card.pivot = (0.5, 0.5)
        card.position = (x + width / 2.0, y + height / 2.0)

        card._hub_title.position = (16.0, 15.0)
        card._hub_description.position = (16.0, 44.0 if compact else 47.0)
        card._hub_button.size = (88.0, 32.0 if compact else 34.0)
        card._hub_button.anchor = (1.0, 0.5)
        card._hub_button.pivot = (0.5, 0.5)
        card._hub_button.position = (-54.0, 0.0)

    def _sync_tools_panel_layout(self, width: float, height: float) -> None:
        margin = 20.0
        self.tools_title.position = (margin, 16.0)
        self.tools_subtitle.position = (margin, 48.0)

        content_top = 84.0
        gap = 12.0
        content_width = max(240.0, width - margin * 2.0)

        # Main Editor is the primary workspace and gets a full-width card.
        main_height = 104.0
        self._layout_tool_card(
            self.scene_button,
            x=margin,
            y=content_top,
            width=content_width,
            height=main_height,
        )

        grid_top = content_top + main_height + gap
        column_gap = 12.0
        column_width = max(150.0, (content_width - column_gap) / 2.0)
        remaining_height = max(190.0, height - grid_top - margin)
        row_height = max(86.0, (remaining_height - gap) / 2.0)

        cards = (
            self.tilemap_button,
            self.item_button,
            self.cutscene_button,
            self.audio_button,
        )
        for index, card in enumerate(cards):
            row = index // 2
            column = index % 2
            self._layout_tool_card(
                card,
                x=margin + column * (column_width + column_gap),
                y=grid_top + row * (row_height + gap),
                width=column_width,
                height=row_height,
                compact=True,
            )
