from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nexora.editor.theme import PANEL_BACKGROUND_DARK, PANEL_BORDER
from nexora.nodes import Button, CheckBox, Dialog, Label, ListView, Panel, TextInput


@dataclass(slots=True, frozen=True)
class NewProjectRequest:
    name: str
    parent: Path
    template: str
    initialize_git: bool
    open_main_editor: bool


class NewProjectWizard(Dialog):
    """Three-step project creation wizard used by the Project Hub."""

    TEMPLATES = (
        (
            "2D Starter",
            "Standard Nexora project with scene, assets, scripts and tests.",
        ),
    )

    def __init__(
        self,
        name: str,
        world,
        *,
        on_browse: Callable[[], None] | None = None,
        on_create: Callable[[NewProjectRequest], bool] | None = None,
    ) -> None:
        super().__init__(name, world)
        self.dialog_size = (780.0, 620.0)
        self.min_dialog_size = (680.0, 560.0)
        self.title = "Create Nexora Project"
        self.close_on_confirm = False
        self.close_on_cancel = False
        self.enter_confirms = False

        self.on_browse = on_browse
        self.on_create_project = on_create
        self._step = 0

        self.step_bar = self.content.create_child("StepBar", node_type=Panel)
        self.step_bar.background = PANEL_BACKGROUND_DARK
        self.step_bar.border_color = PANEL_BORDER
        self.step_bar.border_width = 1.0
        self.step_bar.border_radius = 6.0

        self.step_project = self._step_label("StepProject", "1  Project")
        self.step_options = self._step_label("StepOptions", "2  Options")
        self.step_review = self._step_label("StepReview", "3  Review")

        self.heading = self._label("Heading", "")
        self.heading.scale = 0.88

        self.help_label = self._label("Help", "")
        self.help_label.scale = 0.50

        # Step 1 -------------------------------------------------
        self.name_label = self._label("ProjectNameLabel", "Project name")
        self.name_input = self.content.create_child("ProjectName", node_type=TextInput)
        self.name_input.placeholder = "MyGame"
        self.name_input.on_change = lambda _text: self._update_result_path()
        self.name_input.on_submit = lambda _text: self.confirm()

        self.location_label = self._label("LocationLabel", "Create in folder")
        self.location_input = self.content.create_child("Location", node_type=TextInput)
        self.location_input.placeholder = str(Path.home())
        self.location_input.on_change = lambda _text: self._update_result_path()

        self.browse_button = self.content.create_child("Browse", node_type=Button)
        self.browse_button.text = "Choose Folder..."
        self.browse_button.text_scale = 0.60
        self.browse_button.on_click = self._browse

        self.path_card = self.content.create_child("PathCard", node_type=Panel)
        self.path_card.background = PANEL_BACKGROUND_DARK
        self.path_card.border_color = PANEL_BORDER
        self.path_card.border_width = 1.0
        self.path_card.border_radius = 5.0
        self.path_title = self.path_card.create_child("PathTitle", node_type=Label)
        self.path_title.text = "Project will be created at"
        self.path_title.anchor = (0.0, 0.0)
        self.path_title.pivot = (0.0, 0.0)
        self.path_title.scale = 0.50
        self.path_value = self.path_card.create_child("PathValue", node_type=Label)
        self.path_value.anchor = (0.0, 0.0)
        self.path_value.pivot = (0.0, 0.0)
        self.path_value.scale = 0.52

        # Step 2 -------------------------------------------------
        self.template_label = self._label("TemplateLabel", "Project template")
        self.template_list = self.content.create_child("Templates", node_type=ListView)
        self.template_list.item_height = 58.0
        self.template_list.text_scale = 0.58
        self.template_list.padding_left = 8.0
        self.template_list.padding_right = 8.0
        self.template_list.padding_top = 6.0
        self.template_list.padding_bottom = 6.0
        self.template_list.set_items(
            [f"{title}  -  {description}" for title, description in self.TEMPLATES]
        )
        self.template_list.selected_index = 0

        self.git_checkbox = self.content.create_child("GitInit", node_type=CheckBox)
        self.git_checkbox.text = "Initialize Git repository"
        self.git_checkbox.text_scale = 0.58
        self.git_checkbox.set_checked(False, emit=False)

        self.open_checkbox = self.content.create_child("OpenEditor", node_type=CheckBox)
        self.open_checkbox.text = "Open Nexora Main Editor after creation"
        self.open_checkbox.text_scale = 0.58
        self.open_checkbox.set_checked(True, emit=False)

        # Step 3 -------------------------------------------------
        self.summary_card = self.content.create_child("SummaryCard", node_type=Panel)
        self.summary_card.background = PANEL_BACKGROUND_DARK
        self.summary_card.border_color = PANEL_BORDER
        self.summary_card.border_width = 1.0
        self.summary_card.border_radius = 6.0
        self.summary = self.summary_card.create_child("Summary", node_type=Label)
        self.summary.anchor = (0.0, 0.0)
        self.summary.pivot = (0.0, 0.0)
        self.summary.scale = 0.56

        self.error_label = self._label("Error", "")
        self.error_label.scale = 0.50

        self._sync_step()

    def _label(self, name: str, text: str) -> Label:
        label = self.content.create_child(name, node_type=Label)
        label.text = text
        label.anchor = (0.0, 0.0)
        label.pivot = (0.0, 0.0)
        label.scale = 0.58
        return label

    def _step_label(self, name: str, text: str) -> Label:
        label = self.step_bar.create_child(name, node_type=Label)
        label.text = text
        label.anchor = (0.0, 0.5)
        label.pivot = (0.0, 0.5)
        label.scale = 0.52
        return label

    def _browse(self) -> None:
        if self.on_browse is not None:
            self.on_browse()

    def set_location(self, path: str | Path) -> None:
        self.location_input.set_text(str(Path(path).expanduser().resolve()), emit=False)
        self._update_result_path()

    def show_error(self, message: str) -> None:
        self.error_label.text = str(message)

    def open(self, *, focus=None):
        self._step = 0
        self.error_label.text = ""
        if not self.location_input.text.strip():
            self.location_input.set_text(str(Path.home()), emit=False)
        self._sync_step()
        return super().open(focus=focus or self.name_input)

    def confirm(self) -> None:
        if not self.is_open:
            return

        self.error_label.text = ""
        if self._step == 0:
            if not self._validate_project_info():
                return
            self._step = 1
            self._sync_step()
            return

        if self._step == 1:
            self._step = 2
            self._sync_step()
            return

        request = self._request()
        if request is None:
            return
        callback = self.on_create_project
        if callback is None:
            self.show_error("Project creation callback is not configured.")
            return
        if callback(request):
            self.close()

    def cancel(self) -> None:
        if not self.is_open:
            return
        if self._step > 0:
            self._step -= 1
            self.error_label.text = ""
            self._sync_step()
            return
        self.close()

    def _validate_project_info(self) -> bool:
        name = self.name_input.text.strip()
        if not name:
            self.show_error("Enter a project name.")
            return False

        location = Path(self.location_input.text.strip() or Path.home()).expanduser()
        try:
            location = location.resolve()
        except OSError as exc:
            self.show_error(f"Invalid location: {exc}")
            return False

        if not location.exists():
            self.show_error("Choose an existing parent folder.")
            return False
        if not location.is_dir():
            self.show_error("The project location must be a directory.")
            return False
        if (location / name).exists():
            self.show_error(f"A file or folder named '{name}' already exists there.")
            return False
        return True

    def _request(self) -> NewProjectRequest | None:
        if not self._validate_project_info():
            return None
        template_index = self.template_list.selected_index
        if template_index is None or not (0 <= template_index < len(self.TEMPLATES)):
            template_index = 0
        return NewProjectRequest(
            name=self.name_input.text.strip(),
            parent=Path(self.location_input.text.strip()).expanduser().resolve(),
            template=self.TEMPLATES[template_index][0],
            initialize_git=bool(self.git_checkbox.checked),
            open_main_editor=bool(self.open_checkbox.checked),
        )

    def _update_result_path(self) -> None:
        if not hasattr(self, "path_value"):
            return
        location = self.location_input.text.strip() or str(Path.home())
        name = self.name_input.text.strip() or "<project>"
        self.path_value.text = str(Path(location) / name)

    def _sync_step(self) -> None:
        groups = (
            (
                self.name_label,
                self.name_input,
                self.location_label,
                self.location_input,
                self.browse_button,
                self.path_card,
            ),
            (
                self.template_label,
                self.template_list,
                self.git_checkbox,
                self.open_checkbox,
            ),
            (self.summary_card,),
        )

        for index, controls in enumerate(groups):
            visible = index == self._step
            for control in controls:
                control.visible = visible
                control.enabled = visible

        steps = (self.step_project, self.step_options, self.step_review)
        for index, label in enumerate(steps):
            label.scale = 0.58 if index == self._step else 0.50
            label.text = (
                ("● " if index == self._step else "  ")
                + ("1  Project", "2  Options", "3  Review")[index]
            )

        if self._step == 0:
            self.heading.text = "Project details"
            self.help_label.text = "Name the project and choose the parent folder where it will be created."
            self.cancel_text = "Cancel"
            self.confirm_text = "Next"
            self._update_result_path()
        elif self._step == 1:
            self.heading.text = "Project options"
            self.help_label.text = "Choose the starter template and optional setup actions."
            self.cancel_text = "Back"
            self.confirm_text = "Next"
        else:
            request = self._request()
            if request is not None:
                self.summary.text = (
                    f"Project\n  {request.name}\n\n"
                    f"Location\n  {request.parent / request.name}\n\n"
                    f"Template\n  {request.template}\n\n"
                    f"Git repository\n  {'Yes' if request.initialize_git else 'No'}\n\n"
                    f"Open Main Editor\n  {'Yes' if request.open_main_editor else 'No'}"
                )
            self.heading.text = "Review project"
            self.help_label.text = "Check the settings before Nexora creates the project."
            self.cancel_text = "Back"
            self.confirm_text = "Create Project"

        self.cancel_button.text = self.cancel_text
        self.confirm_button.text = self.confirm_text
        self._sync_layout()

    def _sync_layout(self) -> None:
        # Dialog positions footer buttons from their current size.  The review
        # action uses a longer label than the regular Next button, so size it
        # before the base layout calculates the right-aligned footer.
        self.cancel_button.size = (110.0, 38.0)
        self.confirm_button.size = (
            160.0 if self._step == 2 else 110.0,
            38.0,
        )
        super()._sync_layout()
        width, height = self.content.size
        pad = 8.0
        usable_w = max(0.0, width - pad * 2.0)

        def place(node, left: float, top: float, node_w: float, node_h: float) -> None:
            """Place a centered Nexora UI node from top-left rectangle coordinates."""
            node.anchor = (0.0, 0.0)
            node.pivot = (0.5, 0.5)
            node.size = (max(0.0, node_w), max(0.0, node_h))
            node.position = (
                left + node.size[0] / 2.0,
                top + node.size[1] / 2.0,
            )

        # ------------------------------------------------------
        # Shared header / progress
        # ------------------------------------------------------
        place(self.step_bar, pad, 2.0, usable_w, 42.0)

        third = usable_w / 3.0
        for index, label in enumerate(
            (self.step_project, self.step_options, self.step_review)
        ):
            label.anchor = (0.0, 0.5)
            label.pivot = (0.0, 0.5)
            label.position = (16.0 + third * index, 0.0)

        self.heading.anchor = (0.0, 0.0)
        self.heading.pivot = (0.0, 0.0)
        self.heading.position = (pad, 60.0)

        self.help_label.anchor = (0.0, 0.0)
        self.help_label.pivot = (0.0, 0.0)
        self.help_label.position = (pad, 94.0)

        # ------------------------------------------------------
        # Step 1: project details
        # ------------------------------------------------------
        self.name_label.position = (pad, 132.0)
        place(self.name_input, pad, 156.0, usable_w, 42.0)

        self.location_label.position = (pad, 214.0)
        browse_w = 150.0
        gap = 10.0
        location_w = max(220.0, usable_w - browse_w - gap)
        place(self.location_input, pad, 238.0, location_w, 42.0)
        place(
            self.browse_button,
            pad + location_w + gap,
            238.0,
            browse_w,
            42.0,
        )

        place(self.path_card, pad, 298.0, usable_w, 76.0)
        self.path_title.position = (14.0, 12.0)
        self.path_value.position = (14.0, 40.0)

        # ------------------------------------------------------
        # Step 2: options
        # ------------------------------------------------------
        self.template_label.position = (pad, 132.0)
        place(self.template_list, pad, 158.0, usable_w, 112.0)

        # CheckBox contains its own left-anchored box/label children.
        # Position the CheckBox node itself by its center, otherwise the
        # internal children are shifted left by half the CheckBox width.
        place(self.git_checkbox, pad, 292.0, usable_w, 40.0)
        place(self.open_checkbox, pad, 336.0, usable_w, 40.0)

        # ------------------------------------------------------
        # Step 3: summary
        # ------------------------------------------------------
        place(self.summary_card, pad, 132.0, usable_w, 282.0)
        self.summary.position = (16.0, 12.0)

        # Errors sit above the dialog footer and never overlap controls.
        self.error_label.anchor = (0.0, 0.0)
        self.error_label.pivot = (0.0, 1.0)
        self.error_label.position = (pad, max(398.0, height - 6.0))

