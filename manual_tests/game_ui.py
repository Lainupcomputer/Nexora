from __future__ import annotations

from nexora.core.game import Game
from nexora.nodes import (
    Button,
    CheckBox,
    Slider,
    TextInput,
)
from nexora.scene import Scene


class TestGame(Game):
    def __init__(self) -> None:
        super().__init__()

        self.scene = Scene(
            "GameUITest"
        )

        self._last_focus = None


    # ==============================================================
    # Initialize
    # ==============================================================

    def initialize(self) -> None:
        print("=" * 50)
        print(" Nexora Game UI Workflow Test")
        print("=" * 50)
        print()

        # ======================================================
        # Input A
        # ======================================================

        input_a = self.scene.ui.create_child(
            "InputA",
            node_type=TextInput,
        )

        input_a.anchor = (
            0.5,
            0.5,
        )

        input_a.pivot = (
            0.5,
            0.5,
        )

        input_a.position = (
            0.0,
            -180.0,
        )

        input_a.size = (
            420.0,
            55.0,
        )

        input_a.placeholder = (
            "Type something..."
        )

        # ======================================================
        # Input B
        # ======================================================

        input_b = self.scene.ui.create_child(
            "InputB",
            node_type=TextInput,
        )

        input_b.anchor = (
            0.5,
            0.5,
        )

        input_b.pivot = (
            0.5,
            0.5,
        )

        input_b.position = (
            0.0,
            -100.0,
        )

        input_b.size = (
            420.0,
            55.0,
        )

        input_b.placeholder = (
            "Second input..."
        )

        # ======================================================
        # Button
        # ======================================================

        button = self.scene.ui.create_child(
            "TestButton",
            node_type=Button,
        )

        button.anchor = (
            0.5,
            0.5,
        )

        button.pivot = (
            0.5,
            0.5,
        )

        button.position = (
            0.0,
            -10.0,
        )

        button.size = (
            260.0,
            60.0,
        )

        button.text = (
            "Click me"
        )

        # ======================================================
        # Slider
        # ======================================================

        slider = self.scene.ui.create_child(
            "TestSlider",
            node_type=Slider,
        )

        slider.anchor = (
            0.5,
            0.5,
        )

        slider.pivot = (
            0.5,
            0.5,
        )

        slider.position = (
            0.0,
            90.0,
        )

        slider.min_value = 0.0
        slider.max_value = 100.0
        slider.value = 50.0
        slider.step = 5.0

        slider.length = 400.0
        slider.track_size = 10.0
        slider.handle_size = 28.0

        # ======================================================
        # CheckBox
        # ======================================================

        checkbox = self.scene.ui.create_child(
            "TestCheckBox",
            node_type=CheckBox,
        )

        checkbox.anchor = (
            0.5,
            0.5,
        )

        checkbox.pivot = (
            0.5,
            0.5,
        )

        checkbox.position = (
            0.0,
            180.0,
        )

        checkbox.size = (
            300.0,
            45.0,
        )

        checkbox.text = (
            "Enable feature"
        )

        checkbox.set_checked(
            False,
            emit=False,
        )

        # ======================================================
        # Callbacks
        # ======================================================

        input_a.on_change = lambda text: print(
            f"[InputA] text = {text!r}"
        )

        input_a.on_submit = lambda text: print(
            f"[InputA] submit = {text!r}"
        )

        input_b.on_change = lambda text: print(
            f"[InputB] text = {text!r}"
        )

        input_b.on_submit = lambda text: print(
            f"[InputB] submit = {text!r}"
        )

        button.on_click = lambda: print(
            "[Button] CLICK!"
        )

        slider.on_change = lambda value: print(
            f"[Slider] value = {value:.2f}"
        )

        checkbox.on_change = lambda checked: print(
            f"[CheckBox] checked = {checked}"
        )

        # ======================================================
        # Instructions
        # ======================================================

        print("Test:")
        print()
        print("Mouse:")
        print("  Click InputA")
        print("  Type text")
        print("  Click InputB")
        print("  Type text")
        print("  Click Button")
        print("  Drag Slider")
        print("  Click CheckBox")
        print()
        print("Keyboard:")
        print("  TAB / SHIFT+TAB -> focus navigation")
        print("  ENTER / SPACE   -> button / checkbox")
        print("  Arrow keys      -> slider")
        print()
        print("Expected focus order:")
        print()
        print("  InputA")
        print("    -> InputB")
        print("    -> TestButton")
        print("    -> TestSlider")
        print("    -> TestCheckBox")
        print("    -> InputA")
        print()
        print("ESC should close the game.")
        print()

    # ==============================================================
    # Update
    # ==============================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        super().update(
            delta_time
        )

        current_focus = (
            self.scene.ui.focused_node
        )

        if current_focus is not self._last_focus:
            if current_focus is None:
                print(
                    "[Focus] None"
                )

            else:
                print(
                    f"[Focus] "
                    f"{current_focus.name}"
                )

            self._last_focus = (
                current_focus
            )



def main() -> None:
    game = TestGame()

    game.run()


if __name__ == "__main__":
    main()