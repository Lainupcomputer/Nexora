import pygame

from nexora.input import InputManager
from nexora.threading.context import ThreadContext


def main():
    print("=" * 70)
    print("NEXORA INPUT SYSTEM TEST")
    print("=" * 70)

    pygame.init()
    pygame.display.set_mode((320, 240))

    ThreadContext.initialize()

    input_manager = InputManager()

    input_manager.bind("move_left", "A")
    input_manager.bind("move_left", "LEFT")
    input_manager.bind("move_right", "D")
    input_manager.bind("move_right", "RIGHT")
    input_manager.bind("jump", "SPACE")
    input_manager.bind("shoot", "MOUSE_LEFT")

    input_manager.initialize()

    print()
    print("BINDINGS")
    print("-" * 70)

    print("move_left  -> A / LEFT")
    print("move_right -> D / RIGHT")
    print("jump       -> SPACE")
    print("shoot      -> MOUSE_LEFT")

    print()
    print("EVENT TEST")
    print("-" * 70)

    pygame.event.post(
        pygame.event.Event(
            pygame.KEYDOWN,
            key=pygame.K_a,
        )
    )

    events = pygame.event.get()

    input_manager.begin_frame(events)

    assert input_manager.is_down("move_left")
    assert input_manager.is_pressed("move_left")
    assert not input_manager.is_released("move_left")

    print("✅ Keyboard press")

    input_manager.begin_frame([])

    assert input_manager.is_down("move_left")
    assert not input_manager.is_pressed("move_left")
    assert not input_manager.is_released("move_left")

    print("✅ Keyboard hold")

    pygame.event.post(
        pygame.event.Event(
            pygame.KEYUP,
            key=pygame.K_a,
        )
    )

    input_manager.begin_frame(pygame.event.get())

    assert not input_manager.is_down("move_left")
    assert input_manager.is_released("move_left")

    print("✅ Keyboard release")

    pygame.event.post(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=(100, 120),
        )
    )

    input_manager.begin_frame(pygame.event.get())

    assert input_manager.mouse_down(1)
    assert input_manager.mouse_pressed(1)

    print("✅ Mouse press")

    input_manager.begin_frame([])

    assert input_manager.mouse_down(1)
    assert not input_manager.mouse_pressed(1)

    print("✅ Mouse hold")

    pygame.event.post(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            button=1,
            pos=(100, 120),
        )
    )

    input_manager.begin_frame(pygame.event.get())

    assert not input_manager.mouse_down(1)
    assert input_manager.mouse_released(1)

    print("✅ Mouse release")

    position = input_manager.mouse_position()

    print()
    print("MOUSE")
    print("-" * 70)
    print(f"Position: {position}")

    print()
    print("=" * 70)
    print("INPUT SYSTEM TEST PASSED")
    print("=" * 70)

    pygame.quit()


if __name__ == "__main__":
    main()