from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from nexora.nodes.node import Node


if TYPE_CHECKING:
    from nexora.rendering.renderer import Renderer


Color = tuple[
    float,
    float,
    float,
    float,
]


# ==============================================================
# Enums
# ==============================================================


class NotificationAnchor(str, Enum):
    """
    Screen anchor used by NotificationCenter.
    """

    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"

    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


class NotificationType(str, Enum):
    """
    Visual notification type.
    """

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationState(str, Enum):
    """
    Internal animation state.
    """

    ENTERING = "entering"
    VISIBLE = "visible"
    LEAVING = "leaving"


# ==============================================================
# Notification data
# ==============================================================


@dataclass(slots=True)
class NotificationItem:
    """
    Internal notification instance.
    """

    id: int

    text: str

    title: str | None

    type: NotificationType

    duration: float

    state: NotificationState = (
        NotificationState.ENTERING
    )

    elapsed: float = 0.0

    animation_elapsed: float = 0.0

    x: float = 0.0
    y: float = 0.0

    target_x: float = 0.0
    target_y: float = 0.0

    start_x: float = 0.0
    start_y: float = 0.0

    alpha: float = 0.0


# ==============================================================
# Notification center
# ==============================================================


class NotificationCenter(Node):
    """
    Screen-space notification / toast manager.

    Features:

        - multiple notifications
        - automatic stacking
        - queueing
        - configurable anchor
        - slide animation
        - fade animation
        - configurable visible duration
        - info / success / warning / error styles
        - automatic removal
        - manual dismiss
        - maximum visible notification count

    Example:

        notifications = NotificationCenter(
            "Notifications",
            world,
            renderer,
        )

        notifications.anchor = (
            NotificationAnchor.TOP_RIGHT
        )

        notifications.push(
            "Spiel gespeichert",
            title="Gespeichert",
            type=NotificationType.SUCCESS,
            duration=3.0,
        )
    """

    def __init__(
        self,
        name: str,
        world,
        renderer: Renderer,
    ) -> None:
        super().__init__(
            name,
            world,
        )

        self.renderer = renderer

        # ======================================================
        # State
        # ======================================================

        self.enabled: bool = True

        self._next_id: int = 1

        # ======================================================
        # Anchor
        # ======================================================

        self.anchor: NotificationAnchor = (
            NotificationAnchor.TOP_RIGHT
        )

        # ======================================================
        # Layout
        # ======================================================

        self.width: float = 360.0

        self.height: float = 92.0

        self.margin: float = 24.0

        self.spacing: float = 12.0

        self.padding: float = 18.0

        self.accent_width: float = 5.0

        self.corner_radius: float = 8.0

        # ======================================================
        # Notification count
        # ======================================================

        self.max_visible: int = 5

        # ======================================================
        # Animation
        # ======================================================

        self.slide_enabled: bool = True

        self.fade_enabled: bool = True

        self.enter_duration: float = 0.35

        self.exit_duration: float = 0.30

        # Distance beyond viewport edge.
        self.slide_padding: float = 30.0

        # Speed used when existing notifications change stack
        # position after another item disappears.
        self.stack_smoothing: float = 14.0

        # ======================================================
        # Text
        # ======================================================

        self.title_scale: float = 1.0

        self.text_scale: float = 0.85

        self.title_offset_y: float = -17.0

        self.text_offset_y: float = 16.0

        # ======================================================
        # Colors
        # ======================================================

        self.background_color: Color = (
            0.075,
            0.075,
            0.09,
            0.96,
        )

        self.text_color: Color = (
            0.90,
            0.90,
            0.93,
            1.0,
        )

        self.title_color: Color = (
            1.0,
            1.0,
            1.0,
            1.0,
        )

        self.info_color: Color = (
            0.25,
            0.60,
            1.0,
            1.0,
        )

        self.success_color: Color = (
            0.20,
            0.80,
            0.40,
            1.0,
        )

        self.warning_color: Color = (
            1.0,
            0.70,
            0.15,
            1.0,
        )

        self.error_color: Color = (
            0.95,
            0.22,
            0.22,
            1.0,
        )

        # ======================================================
        # Progress bar
        # ======================================================

        self.show_progress: bool = True

        self.progress_height: float = 3.0

        # ======================================================
        # Queues
        # ======================================================

        self._pending: deque[
            NotificationItem
        ] = deque()

        self._active: list[
            NotificationItem
        ] = []

    # ==========================================================
    # Public state
    # ==========================================================

    @property
    def active_count(
        self,
    ) -> int:
        return len(
            self._active
        )

    @property
    def pending_count(
        self,
    ) -> int:
        return len(
            self._pending
        )

    @property
    def count(
        self,
    ) -> int:
        return (
            len(
                self._active
            )
            + len(
                self._pending
            )
        )

    @property
    def empty(
        self,
    ) -> bool:
        return (
            not self._active
            and not self._pending
        )

    # ==========================================================
    # Push
    # ==========================================================

    def push(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
        type: NotificationType | str = NotificationType.INFO,
    ) -> int:
        """
        Queue a notification.

        Returns the generated notification ID.

        Example:

            notification_id = notifications.push(
                "Quest abgeschlossen",
                title="Quest",
                duration=4.0,
                type="success",
            )
        """

        duration = float(
            duration
        )

        if duration < 0.0:
            raise ValueError(
                "Notification duration cannot be negative."
            )

        notification_type = (
            NotificationType(
                type
            )
        )

        notification_id = (
            self._next_id
        )

        self._next_id += 1

        item = NotificationItem(
            id=notification_id,
            text=str(
                text
            ),
            title=(
                None
                if title is None
                else str(
                    title
                )
            ),
            type=notification_type,
            duration=duration,
        )

        self._pending.append(
            item
        )

        self._promote_pending()

        return notification_id

    # ==========================================================
    # Convenience push methods
    # ==========================================================

    def info(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
    ) -> int:
        return self.push(
            text,
            title=title,
            duration=duration,
            type=NotificationType.INFO,
        )

    def success(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
    ) -> int:
        return self.push(
            text,
            title=title,
            duration=duration,
            type=NotificationType.SUCCESS,
        )

    def warning(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
    ) -> int:
        return self.push(
            text,
            title=title,
            duration=duration,
            type=NotificationType.WARNING,
        )

    def error(
        self,
        text: str,
        *,
        title: str | None = None,
        duration: float = 3.0,
    ) -> int:
        return self.push(
            text,
            title=title,
            duration=duration,
            type=NotificationType.ERROR,
        )

    # ==========================================================
    # Dismiss
    # ==========================================================

    def dismiss(
        self,
        notification_id: int,
    ) -> bool:
        """
        Start dismiss animation for a notification.

        Returns True when the notification was found.
        """

        # ------------------------------------------------------
        # Active
        # ------------------------------------------------------

        for item in self._active:
            if item.id != notification_id:
                continue

            self._start_leaving(
                item
            )

            return True

        # ------------------------------------------------------
        # Pending
        # ------------------------------------------------------

        for item in tuple(
            self._pending
        ):
            if item.id != notification_id:
                continue

            self._pending.remove(
                item
            )

            return True

        return False

    def dismiss_all(
        self,
    ) -> None:
        """
        Animate all active notifications out and remove all
        queued notifications.
        """

        self._pending.clear()

        for item in self._active:
            self._start_leaving(
                item
            )

    def clear(
        self,
    ) -> None:
        """
        Immediately remove all notifications.
        """

        self._pending.clear()
        self._active.clear()

    # ==========================================================
    # Queue management
    # ==========================================================

    def _promote_pending(
        self,
    ) -> None:
        while (
            self._pending
            and len(
                self._active
            )
            < self.max_visible
        ):
            item = (
                self._pending.popleft()
            )

            self._prepare_enter(
                item
            )

            self._active.append(
                item
            )

        self._update_targets()

    # ==========================================================
    # Position calculation
    # ==========================================================

    def _target_position(
        self,
        index: int,
    ) -> tuple[
        float,
        float,
    ]:
        screen_width = float(
            self.renderer.width
        )

        screen_height = float(
            self.renderer.height
        )

        anchor = (
            NotificationAnchor(
                self.anchor
            )
        )

        # ------------------------------------------------------
        # Horizontal position
        # ------------------------------------------------------

        if anchor in {
            NotificationAnchor.TOP_LEFT,
            NotificationAnchor.BOTTOM_LEFT,
        }:
            x = (
                self.margin
                + self.width
                * 0.5
            )

        elif anchor in {
            NotificationAnchor.TOP_RIGHT,
            NotificationAnchor.BOTTOM_RIGHT,
        }:
            x = (
                screen_width
                - self.margin
                - self.width
                * 0.5
            )

        else:
            x = (
                screen_width
                * 0.5
            )

        # ------------------------------------------------------
        # Vertical position
        # ------------------------------------------------------

        step = (
            self.height
            + self.spacing
        )

        if anchor in {
            NotificationAnchor.TOP_LEFT,
            NotificationAnchor.TOP_CENTER,
            NotificationAnchor.TOP_RIGHT,
        }:
            y = (
                self.margin
                + self.height
                * 0.5
                + index
                * step
            )

        else:
            y = (
                screen_height
                - self.margin
                - self.height
                * 0.5
                - index
                * step
            )

        return (
            x,
            y,
        )

    def _outside_position(
        self,
        target_x: float,
        target_y: float,
    ) -> tuple[
        float,
        float,
    ]:
        screen_width = float(
            self.renderer.width
        )

        screen_height = float(
            self.renderer.height
        )

        anchor = (
            NotificationAnchor(
                self.anchor
            )
        )

        # ------------------------------------------------------
        # Left anchors
        # ------------------------------------------------------

        if anchor in {
            NotificationAnchor.TOP_LEFT,
            NotificationAnchor.BOTTOM_LEFT,
        }:
            return (
                -self.width
                * 0.5
                - self.slide_padding,
                target_y,
            )

        # ------------------------------------------------------
        # Right anchors
        # ------------------------------------------------------

        if anchor in {
            NotificationAnchor.TOP_RIGHT,
            NotificationAnchor.BOTTOM_RIGHT,
        }:
            return (
                screen_width
                + self.width
                * 0.5
                + self.slide_padding,
                target_y,
            )

        # ------------------------------------------------------
        # Top center
        # ------------------------------------------------------

        if (
            anchor
            == NotificationAnchor.TOP_CENTER
        ):
            return (
                target_x,
                -self.height
                * 0.5
                - self.slide_padding,
            )

        # ------------------------------------------------------
        # Bottom center
        # ------------------------------------------------------

        return (
            target_x,
            screen_height
            + self.height
            * 0.5
            + self.slide_padding,
        )

    def _update_targets(
        self,
    ) -> None:
        for index, item in enumerate(
            self._active
        ):
            (
                item.target_x,
                item.target_y,
            ) = self._target_position(
                index
            )

    # ==========================================================
    # Enter
    # ==========================================================

    def _prepare_enter(
        self,
        item: NotificationItem,
    ) -> None:
        item.state = (
            NotificationState.ENTERING
        )

        item.elapsed = 0.0
        item.animation_elapsed = 0.0

        index = len(
            self._active
        )

        (
            item.target_x,
            item.target_y,
        ) = self._target_position(
            index
        )

        if self.slide_enabled:
            (
                item.x,
                item.y,
            ) = self._outside_position(
                item.target_x,
                item.target_y,
            )

        else:
            item.x = (
                item.target_x
            )

            item.y = (
                item.target_y
            )

        item.start_x = item.x
        item.start_y = item.y

        item.alpha = (
            0.0
            if self.fade_enabled
            else 1.0
        )

    # ==========================================================
    # Leave
    # ==========================================================

    def _start_leaving(
        self,
        item: NotificationItem,
    ) -> None:
        if (
            item.state
            == NotificationState.LEAVING
        ):
            return

        item.state = (
            NotificationState.LEAVING
        )

        item.animation_elapsed = 0.0

        item.start_x = item.x
        item.start_y = item.y

        (
            item.target_x,
            item.target_y,
        ) = self._outside_position(
            item.x,
            item.y,
        )

    # ==========================================================
    # Easing
    # ==========================================================

    @staticmethod
    def _ease_out_cubic(
        value: float,
    ) -> float:
        value = max(
            0.0,
            min(
                1.0,
                value,
            ),
        )

        inverse = (
            1.0
            - value
        )

        return (
            1.0
            - inverse
            * inverse
            * inverse
        )

    @staticmethod
    def _ease_in_cubic(
        value: float,
    ) -> float:
        value = max(
            0.0,
            min(
                1.0,
                value,
            ),
        )

        return (
            value
            * value
            * value
        )

    @staticmethod
    def _lerp(
        start: float,
        end: float,
        amount: float,
    ) -> float:
        return (
            start
            + (
                end
                - start
            )
            * amount
        )

    # ==========================================================
    # Update entering
    # ==========================================================

    def _update_entering(
        self,
        item: NotificationItem,
        delta_time: float,
    ) -> None:
        if self.enter_duration <= 0.0:
            progress = 1.0

        else:
            item.animation_elapsed += (
                delta_time
            )

            progress = min(
                item.animation_elapsed
                / self.enter_duration,
                1.0,
            )

        eased = self._ease_out_cubic(
            progress
        )

        if self.slide_enabled:
            item.x = self._lerp(
                item.start_x,
                item.target_x,
                eased,
            )

            item.y = self._lerp(
                item.start_y,
                item.target_y,
                eased,
            )

        else:
            item.x = (
                item.target_x
            )

            item.y = (
                item.target_y
            )

        if self.fade_enabled:
            item.alpha = eased

        else:
            item.alpha = 1.0

        if progress >= 1.0:
            item.x = (
                item.target_x
            )

            item.y = (
                item.target_y
            )

            item.alpha = 1.0

            item.elapsed = 0.0

            item.state = (
                NotificationState.VISIBLE
            )

    # ==========================================================
    # Update visible
    # ==========================================================

    def _update_visible(
        self,
        item: NotificationItem,
        delta_time: float,
    ) -> None:
        item.elapsed += (
            delta_time
        )

        # ------------------------------------------------------
        # Smooth stack repositioning
        # ------------------------------------------------------

        amount = min(
            1.0,
            self.stack_smoothing
            * delta_time,
        )

        item.x = self._lerp(
            item.x,
            item.target_x,
            amount,
        )

        item.y = self._lerp(
            item.y,
            item.target_y,
            amount,
        )

        if (
            item.elapsed
            >= item.duration
        ):
            self._start_leaving(
                item
            )

    # ==========================================================
    # Update leaving
    # ==========================================================

    def _update_leaving(
        self,
        item: NotificationItem,
        delta_time: float,
    ) -> bool:
        if self.exit_duration <= 0.0:
            progress = 1.0

        else:
            item.animation_elapsed += (
                delta_time
            )

            progress = min(
                item.animation_elapsed
                / self.exit_duration,
                1.0,
            )

        eased = self._ease_in_cubic(
            progress
        )

        if self.slide_enabled:
            item.x = self._lerp(
                item.start_x,
                item.target_x,
                eased,
            )

            item.y = self._lerp(
                item.start_y,
                item.target_y,
                eased,
            )

        if self.fade_enabled:
            item.alpha = (
                1.0
                - eased
            )

        if progress >= 1.0:
            return True

        return False

    # ==========================================================
    # Update
    # ==========================================================

    def update(
        self,
        delta_time: float,
    ) -> None:
        if not self.enabled:
            return

        self._promote_pending()

        self._update_targets()

        finished: list[
            NotificationItem
        ] = []

        for item in self._active:
            if (
                item.state
                == NotificationState.ENTERING
            ):
                self._update_entering(
                    item,
                    delta_time,
                )

            elif (
                item.state
                == NotificationState.VISIBLE
            ):
                self._update_visible(
                    item,
                    delta_time,
                )

            elif (
                item.state
                == NotificationState.LEAVING
            ):
                if self._update_leaving(
                    item,
                    delta_time,
                ):
                    finished.append(
                        item
                    )

        # ------------------------------------------------------
        # Remove finished items
        # ------------------------------------------------------

        if finished:
            for item in finished:
                if item in self._active:
                    self._active.remove(
                        item
                    )

            self._update_targets()

            self._promote_pending()

    # ==========================================================
    # Style
    # ==========================================================

    def _accent_color(
        self,
        notification_type: NotificationType,
    ) -> Color:
        if (
            notification_type
            == NotificationType.SUCCESS
        ):
            return self.success_color

        if (
            notification_type
            == NotificationType.WARNING
        ):
            return self.warning_color

        if (
            notification_type
            == NotificationType.ERROR
        ):
            return self.error_color

        return self.info_color

    @staticmethod
    def _with_alpha(
        color: Color,
        alpha: float,
    ) -> Color:
        return (
            color[0],
            color[1],
            color[2],
            color[3]
            * alpha,
        )

    # ==========================================================
    # Screen-space conversion
    # ==========================================================

    def _screen_to_world(
        self,
        x: float,
        y: float,
    ) -> tuple[
        float,
        float,
    ]:
        """
        Convert viewport coordinates into coordinates that remain
        visually fixed on screen with the current renderer camera.
        """

        camera = (
            self.renderer.camera
        )

        zoom = max(
            float(
                camera.zoom
            ),
            0.0001,
        )

        center_x = (
            float(
                self.renderer.width
            )
            * 0.5
        )

        center_y = (
            float(
                self.renderer.height
            )
            * 0.5
        )

        shake_x = float(
            getattr(
                camera,
                "shake_x",
                0.0,
            )
        )

        shake_y = float(
            getattr(
                camera,
                "shake_y",
                0.0,
            )
        )

        world_x = (
            float(
                camera.x
            )
            - shake_x
            + (
                x
                - center_x
            )
            / zoom
        )

        world_y = (
            float(
                camera.y
            )
            - shake_y
            + (
                y
                - center_y
            )
            / zoom
        )

        return (
            world_x,
            world_y,
        )

    # ==========================================================
    # Render rectangle
    # ==========================================================

    def _render_rect(
        self,
        screen_x: float,
        screen_y: float,
        width: float,
        height: float,
        *,
        color: Color,
        radius: float = 0.0,
    ) -> None:
        camera = (
            self.renderer.camera
        )

        zoom = max(
            float(
                camera.zoom
            ),
            0.0001,
        )

        world_x, world_y = (
            self._screen_to_world(
                screen_x,
                screen_y,
            )
        )

        self.renderer.rect(
            world_x,
            world_y,
            width / zoom,
            height / zoom,
            color=color,
            radius=(
                radius
                / zoom
            ),
            origin=(
                0.5,
                0.5,
            ),
        )

    # ==========================================================
    # Render text
    # ==========================================================

    def _render_text(
        self,
        text: str,
        screen_x: float,
        screen_y: float,
        *,
        color: Color,
        scale: float,
    ) -> None:
        """
        Render text at a screen-space position.

        GPUTextRenderer uses a centered coordinate system:

            0, 0 = viewport center

        NotificationCenter however uses conventional screen
        coordinates:

            0, 0 = top-left

        Therefore only a screen-space -> centered-space conversion
        is required here. Camera position must NOT be applied.
        """

        x = (
            float(screen_x)
            - float(self.renderer.width)
            * 0.5
        )

        y = (
            float(screen_y)
            - float(self.renderer.height)
            * 0.5
        )

        self.renderer.text(
            text,
            x,
            y,
            scale=float(
                scale
            ),
        )

    # ==========================================================
    # Progress
    # ==========================================================

    def _progress(
        self,
        item: NotificationItem,
    ) -> float:
        if item.duration <= 0.0:
            return 0.0

        return max(
            0.0,
            min(
                1.0,
                1.0
                - item.elapsed
                / item.duration,
            ),
        )

    # ==========================================================
    # Render item
    # ==========================================================

    def _render_item(
        self,
        item: NotificationItem,
    ) -> None:
        alpha = max(
            0.0,
            min(
                1.0,
                item.alpha,
            ),
        )

        accent = (
            self._accent_color(
                item.type
            )
        )

        # ------------------------------------------------------
        # Background
        # ------------------------------------------------------

        self._render_rect(
            item.x,
            item.y,
            self.width,
            self.height,
            color=self._with_alpha(
                self.background_color,
                alpha,
            ),
            radius=self.corner_radius,
        )

        # ------------------------------------------------------
        # Accent bar
        # ------------------------------------------------------

        accent_x = (
            item.x
            - self.width
            * 0.5
            + self.accent_width
            * 0.5
        )

        self._render_rect(
            accent_x,
            item.y,
            self.accent_width,
            self.height,
            color=self._with_alpha(
                accent,
                alpha,
            ),
            radius=0.0,
        )

        # ------------------------------------------------------
        # Text position
        # ------------------------------------------------------

        text_x = (
            item.x
            - self.width
            * 0.5
            + self.padding
            + self.accent_width
        )

        # ------------------------------------------------------
        # Title + message
        # ------------------------------------------------------

        if item.title:
            self._render_text(
                item.title,
                text_x,
                item.y
                + self.title_offset_y,
                color=self._with_alpha(
                    self.title_color,
                    alpha,
                ),
                scale=self.title_scale,
            )

            self._render_text(
                item.text,
                text_x,
                item.y
                + self.text_offset_y,
                color=self._with_alpha(
                    self.text_color,
                    alpha,
                ),
                scale=self.text_scale,
            )

        else:
            self._render_text(
                item.text,
                text_x,
                item.y,
                color=self._with_alpha(
                    self.text_color,
                    alpha,
                ),
                scale=self.text_scale,
            )

        # ------------------------------------------------------
        # Remaining-time progress bar
        # ------------------------------------------------------

        if (
            self.show_progress
            and item.state
            == NotificationState.VISIBLE
        ):
            progress = (
                self._progress(
                    item
                )
            )

            progress_width = (
                self.width
                * progress
            )

            if progress_width > 0.0:
                progress_x = (
                    item.x
                    - self.width
                    * 0.5
                    + progress_width
                    * 0.5
                )

                progress_y = (
                    item.y
                    + self.height
                    * 0.5
                    - self.progress_height
                    * 0.5
                )

                self._render_rect(
                    progress_x,
                    progress_y,
                    progress_width,
                    self.progress_height,
                    color=self._with_alpha(
                        accent,
                        alpha,
                    ),
                )

    # ==========================================================
    # Render
    # ==========================================================

    def render(
        self,
        renderer,
        interpolation: float,
    ) -> None:
        if not self.enabled:
            return

        for item in self._active:
            self._render_item(
                item
            )