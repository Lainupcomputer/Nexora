from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from nexora.debug.console.autocomplete import AutocompleteEngine
from nexora.debug.console.command import CommandContext
from nexora.debug.console.history import CommandHistory
from nexora.debug.console.log_bridge import ConsoleLogBridge
from nexora.debug.console.parser import parse_command
from nexora.debug.console.registry import CommandRegistry
from nexora.debug.console.renderer import DebugConsoleRenderer


class ConsoleLevel(Enum):
    OUTPUT = "OUTPUT"
    INFO = "INFO"
    DEBUG = "DEBUG"
    WARNING = "WARN"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class ConsoleLine:
    text: str
    level: ConsoleLevel = ConsoleLevel.OUTPUT

    @property
    def display_text(self) -> str:
        if self.level is ConsoleLevel.OUTPUT:
            return self.text
        return f"[{self.level.value}] {self.text}"

    @property
    def alpha(self) -> float:
        if self.level is ConsoleLevel.DEBUG:
            return 0.72
        if self.level is ConsoleLevel.WARNING:
            return 0.90
        return 1.0


class DebugConsole:
    """
    Global, scene-independent Nexora debug console.

    It belongs directly to Engine. The open/close action comes from the
    normal layered input bindings. Internal editing keys are fixed while
    the console is open.
    """

    OPEN_ACTION = "debug_console"

    def __init__(self, engine) -> None:
        self.engine = engine
        self.registry = CommandRegistry()
        self.history = CommandHistory(max_entries=200)
        self.autocomplete = AutocompleteEngine(self.registry)
        self.renderer = DebugConsoleRenderer()

        self._open = False
        self.input_text = ""
        self._lines: list[ConsoleLine] = []
        self.max_lines = 1000
        self.scroll_offset = 0
        self._last_blink = time.monotonic()
        self.cursor_visible = True
        self._release_capture_after_frame = False

        self._log_bridge = ConsoleLogBridge(self, engine)
        self._log_bridge.attach()

        self._register_builtin_commands()

    # ==========================================================
    # Visibility / capture
    # ==========================================================

    @property
    def is_open(self) -> bool:
        return self._open

    def toggle(self) -> bool:
        if self._open:
            self.close()
        else:
            self.open()
        return self._open

    def open(self) -> None:
        if self._open:
            return

        self._open = True
        self._release_capture_after_frame = False
        self.scroll_offset = 0
        self.autocomplete.reset()
        self.engine.input.set_action_capture(
            True,
            allowed_actions={self.OPEN_ACTION},
        )

        try:
            acquire = getattr(
                self.engine.input,
                "acquire_text_input",
                None,
            )
            if acquire is not None:
                acquire(self)
            else:
                self.engine.input.start_text_input()
        except RuntimeError:
            pass

    def close(self, *, defer_capture_release: bool = False) -> None:
        if not self._open:
            return

        self._open = False
        self.autocomplete.reset()

        release = getattr(
            self.engine.input,
            "release_text_input",
            None,
        )
        if release is not None:
            release(self)
        else:
            self.engine.input.stop_text_input()

        # Keep gameplay actions suppressed until the frame ends. Without
        # this, ESC would close the console and then trigger the game's
        # pause action during the very same update.
        if defer_capture_release:
            self._release_capture_after_frame = True
        else:
            self._release_capture_after_frame = False
            self.engine.input.set_action_capture(False)

    def end_frame(self) -> None:
        if self._release_capture_after_frame:
            self._release_capture_after_frame = False
            self.engine.input.set_action_capture(False)

    # ==========================================================
    # Output
    # ==========================================================

    @property
    def lines(self) -> tuple[ConsoleLine, ...]:
        return tuple(self._lines)

    def clear(self) -> None:
        self._lines.clear()
        self.scroll_offset = 0

    def _append(self, text: object, level: ConsoleLevel) -> None:
        message = str(text)
        split = message.splitlines() or [""]
        self._lines.extend(ConsoleLine(line, level) for line in split)

        if len(self._lines) > self.max_lines:
            del self._lines[: len(self._lines) - self.max_lines]

        self.scroll_offset = 0

    def write(self, text: object) -> None:
        self._append(text, ConsoleLevel.OUTPUT)

    def info(self, text: object) -> None:
        self._append(text, ConsoleLevel.INFO)

    def debug(self, text: object) -> None:
        self._append(text, ConsoleLevel.DEBUG)

    def warning(self, text: object) -> None:
        self._append(text, ConsoleLevel.WARNING)

    def error(
        self,
        text: object,
        *,
        title: str = "Engine Error",
        duration: float = 6.0,
    ) -> None:
        self._append(text, ConsoleLevel.ERROR)
        self._notify_error(
            text,
            title=title,
            duration=duration,
        )

    def _notify_error(
        self,
        text: object,
        *,
        title: str = "Engine Error",
        duration: float = 6.0,
    ) -> None:
        """Mirror console errors to the global notification overlay.

        The notification overlay is owned by Game and may not exist yet
        during very early engine startup or shutdown. In that case the
        console error is still kept, but no toast is attempted.
        """
        game = getattr(self.engine, "game", None)
        if game is None:
            return

        # Real Game exposes ``notifications`` as a property once the
        # global overlay is initialized. Tests and very early startup may
        # only have the backing ``_notifications`` attribute. Support both.
        try:
            notifications = game.notifications
        except (AttributeError, RuntimeError):
            notifications = getattr(
                game,
                "_notifications",
                None,
            )

        if notifications is None:
            return

        try:
            notifications.error(
                str(text),
                title=title,
                duration=duration,
            )
        except Exception:
            # A notification failure must never break the debug console
            # or recurse back into the logger.
            pass

    # ==========================================================
    # Commands
    # ==========================================================

    def register_command(self, name, handler, **kwargs):
        return self.registry.register(name, handler, **kwargs)

    def unregister_command(self, name: str) -> bool:
        return self.registry.unregister(name)

    def execute(self, text: str) -> bool:
        text = str(text).strip()

        if not text:
            return False

        self.write(f"> {text}")
        self.history.add(text)
        self.autocomplete.reset()

        try:
            parsed = parse_command(text)
        except ValueError as exc:
            self.error(f"Parse error: {exc}")
            return False

        if parsed is None:
            return False

        command = self.registry.get(parsed.name)

        if command is None:
            self.error(
                f"Unknown command: {parsed.name}. Type 'help' for commands."
            )
            return False

        context = CommandContext(
            console=self,
            engine=self.engine,
            command=command.name,
            args=parsed.args,
            raw=parsed.raw,
        )

        try:
            result = command.handler(context)
        except Exception as exc:
            message = (
                f"Console command '{command.name}' failed: "
                f"{type(exc).__name__}: {exc}"
            )
            logger = getattr(self.engine, "logger", None)
            if logger is not None:
                logger.error(message)
            else:
                self.error(message)
            return False

        if result is not None:
            self.write(result)

        return True

    # ==========================================================
    # Input
    # ==========================================================

    def update(self, delta_time: float) -> None:
        del delta_time

        now = time.monotonic()
        if now - self._last_blink >= 0.5:
            self.cursor_visible = not self.cursor_visible
            self._last_blink = now

        if not self._open:
            return

        input_manager = self.engine.input

        # A Scene may also manage SDL text input for focused TextInput
        # controls. The console owns a persistent request while open, so
        # keep SDL text input active independently of the active Scene.
        try:
            input_manager.start_text_input()
        except RuntimeError:
            pass

        # Text produced by SDL_TEXT_INPUT includes keyboard layout,
        # modifiers and Unicode handling, so normal characters do not need
        # to be mapped manually.
        changed = False
        for chunk in input_manager.text_input:
            if chunk:
                self.input_text += chunk
                changed = True

        if changed:
            self.history.reset_navigation()
            self.autocomplete.reset()
            self.scroll_offset = 0

        # Fixed console editing/navigation keys.
        if input_manager.key_pressed("escape"):
            self.close(defer_capture_release=True)
            return

        if input_manager.key_pressed("enter"):
            command = self.input_text
            self.input_text = ""
            self.scroll_offset = 0
            if command.strip():
                self.execute(command)
            return

        if input_manager.key_pressed("backspace"):
            if self.input_text:
                self.input_text = self.input_text[:-1]
            self.history.reset_navigation()
            self.autocomplete.reset()

        if input_manager.key_pressed("up"):
            self.input_text = self.history.previous(self.input_text)
            self.autocomplete.reset()

        if input_manager.key_pressed("down"):
            self.input_text = self.history.next(self.input_text)
            self.autocomplete.reset()

        if input_manager.key_pressed("page up"):
            self.scroll_offset = min(
                max(0, len(self._lines) - 1),
                self.scroll_offset + 5,
            )

        if input_manager.key_pressed("page down"):
            self.scroll_offset = max(0, self.scroll_offset - 5)

        if input_manager.key_pressed("tab"):
            result = self.autocomplete.complete(self.input_text)
            self.input_text = result.text

            # Multiple matches are cycled silently on repeated Tab.
            # Autocomplete must not mutate the output log.

    def consumes_event(self, event) -> bool:
        if not (
            self._open
            or self._release_capture_after_frame
        ):
            return False

        try:
            import sdl3
        except ImportError:
            return False

        event_type = getattr(event, "type", None)
        return event_type in {
            sdl3.SDL_EVENT_KEY_DOWN,
            sdl3.SDL_EVENT_KEY_UP,
            sdl3.SDL_EVENT_TEXT_INPUT,
        }

    # ==========================================================
    # Rendering
    # ==========================================================

    def render(self, renderer) -> None:
        self.renderer.render(renderer, self)

    def visible_lines(self, count: int) -> tuple[ConsoleLine, ...]:
        count = max(1, int(count))
        end = max(0, len(self._lines) - self.scroll_offset)
        start = max(0, end - count)
        return tuple(self._lines[start:end])

    # ==========================================================
    # Builtins
    # ==========================================================

    def _register_builtin_commands(self) -> None:
        self.register_command(
            "help",
            self._cmd_help,
            description="List commands or show help for one command.",
            usage="help [command]",
            completer=self._complete_command_name,
        )
        self.register_command(
            "clear",
            self._cmd_clear,
            description="Clear console output.",
        )
        self.register_command(
            "quit",
            self._cmd_quit,
            description="Stop the running game.",
            aliases=("exit",),
        )
        self.register_command(
            "fps",
            self._cmd_fps,
            description="Show current and target FPS.",
        )
        self.register_command(
            "timescale",
            self._cmd_timescale,
            description="Show or change engine time scale.",
            usage="timescale [value]",
        )
        self.register_command(
            "scene",
            self._cmd_scene,
            description="Show the active scene.",
        )
        self.register_command(
            "nodes",
            self._cmd_nodes,
            description="Print the active scene node tree.",
        )

    def _complete_command_name(self, args, prefix) -> Iterable[str]:
        del args
        return self.registry.matches(prefix)

    def _cmd_help(self, ctx: CommandContext):
        if ctx.args:
            command = self.registry.get(ctx.args[0])
            if command is None:
                ctx.error(f"Unknown command: {ctx.args[0]}")
                return None

            usage = command.usage or command.name
            ctx.write(usage)
            if command.description:
                ctx.write(command.description)
            if command.aliases:
                ctx.write("Aliases: " + ", ".join(command.aliases))
            return None

        ctx.write("Commands:")
        for command in self.registry.commands():
            description = command.description or ""
            ctx.write(f"  {command.name:<12} {description}".rstrip())
        return None

    def _cmd_clear(self, ctx: CommandContext):
        del ctx
        self.clear()
        return None

    def _cmd_quit(self, ctx: CommandContext):
        del ctx
        self.engine.stop()
        return None

    def _cmd_fps(self, ctx: CommandContext):
        metrics = getattr(self.engine.debug_overlay, "metrics", None)
        current = 0.0
        if metrics is not None:
            current = float(getattr(metrics.snapshot, "fps", 0.0))
        target = int(self.engine.loop.target_fps)
        return f"FPS: {current:.1f} / {target}"

    def _cmd_timescale(self, ctx: CommandContext):
        if not ctx.args:
            return f"Time scale: {self.engine.time.time_scale:.3f}"

        try:
            value = float(ctx.args[0])
        except ValueError:
            ctx.error("timescale expects a number")
            return None

        if not math.isfinite(value) or value < 0.0:
            ctx.error("timescale must be a finite value >= 0")
            return None

        self.engine.time.time_scale = value
        return f"Time scale set to {value:.3f}"

    def _cmd_scene(self, ctx: CommandContext):
        del ctx
        scene = getattr(self.engine.game, "scene", None)
        if scene is None:
            return "Scene: <none>"
        return f"Scene: {getattr(scene, 'name', '<unnamed>')}"

    def _cmd_nodes(self, ctx: CommandContext):
        del ctx
        scene = getattr(self.engine.game, "scene", None)
        root = getattr(scene, "root", None) if scene is not None else None

        if root is None:
            return "No active scene root."

        self.write("Node tree:")
        self._write_node_tree(root)
        return None

    def _write_node_tree(self, node, depth: int = 0) -> None:
        name = getattr(node, "name", node.__class__.__name__)
        self.write(f"{'  ' * depth}- {name} [{node.__class__.__name__}]")

        children = getattr(node, "children", ())
        try:
            iterable = tuple(children)
        except TypeError:
            iterable = ()

        for child in iterable:
            self._write_node_tree(child, depth + 1)

    def shutdown(self) -> None:
        self._log_bridge.detach()

        if self._open:
            self.close(
                defer_capture_release=False
            )
        elif self._release_capture_after_frame:
            self._release_capture_after_frame = False
            self.engine.input.set_action_capture(False)
