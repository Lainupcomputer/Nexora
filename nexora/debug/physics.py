from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from nexora.nodes.node import Node


class PhysicsDebugRenderer:
    """
    Debug renderer for Nexora 2D physics.

    Supported visualization:

        - CollisionShape2D rectangles
        - CharacterBody2D
        - StaticBody2D
        - Area2D
        - Body origins
        - Character velocity
        - Kinematic collision contacts
        - Kinematic collision normals
        - RayCast2D rays
        - RayCast2D hit points
        - RayCast2D hit normals

    Physics debug rendering is completely separate from normal
    Node rendering.
    """

    def __init__(
        self,
    ) -> None:
        # ======================================================
        # Visibility
        # ======================================================

        self.visible: bool = False

        self.shapes: bool = True
        self.areas: bool = True

        self.origins: bool = True
        self.velocity: bool = True

        self.contacts: bool = True
        self.normals: bool = True

        self.rays: bool = True
        self.ray_hits: bool = True

        # ======================================================
        # Appearance
        # ======================================================

        self.line_width: float = 2.0

        self.origin_size: float = 4.0
        self.contact_size: float = 5.0

        self.velocity_scale: float = 0.15

        self.normal_length: float = 28.0

        self.ray_origin_size: float = 4.0
        self.ray_hit_size: float = 5.0
        self.ray_normal_length: float = 24.0

        # ======================================================
        # Body colors
        # ======================================================

        self.character_color = (
            0.2,
            1.0,
            0.3,
            1.0,
        )

        self.static_color = (
            1.0,
            0.25,
            0.25,
            1.0,
        )

        self.area_color = (
            0.2,
            0.65,
            1.0,
            1.0,
        )

        self.body_color = (
            1.0,
            0.9,
            0.2,
            1.0,
        )

        # ======================================================
        # Generic debug colors
        # ======================================================

        self.origin_color = (
            1.0,
            1.0,
            1.0,
            1.0,
        )

        self.velocity_color = (
            1.0,
            0.5,
            0.1,
            1.0,
        )

        self.contact_color = (
            1.0,
            0.0,
            1.0,
            1.0,
        )

        self.normal_color = (
            0.0,
            1.0,
            1.0,
            1.0,
        )

        # ======================================================
        # Ray colors
        # ======================================================

        self.ray_color = (
            1.0,
            0.85,
            0.1,
            1.0,
        )

        self.ray_hit_color = (
            1.0,
            0.1,
            0.1,
            1.0,
        )

        self.ray_miss_color = (
            0.7,
            0.7,
            0.7,
            1.0,
        )

        self.ray_normal_color = (
            0.1,
            1.0,
            1.0,
            1.0,
        )

    # ==============================================================
    # Visibility
    # ==============================================================

    def toggle(
        self,
    ) -> bool:
        self.visible = (
            not self.visible
        )

        return self.visible

    def show(
        self,
    ) -> None:
        self.visible = True

    def hide(
        self,
    ) -> None:
        self.visible = False

    # ==============================================================
    # Render
    # ==============================================================

    def render(
        self,
        renderer,
        root: Node | None,
    ) -> None:
        """
        Render all physics debug information for a Node tree.
        """

        if not self.visible:
            return

        if root is None:
            return

        from nexora.nodes.entity import (
            Area2D,
            Body2D,
            CharacterBody2D,
            CollisionShape2D,
            RayCast2D,
        )

        for node in root.iter_tree():
            if not node.enabled:
                continue

            # ==================================================
            # RayCast2D
            # ==================================================

            if isinstance(
                node,
                RayCast2D,
            ):
                if self.rays:
                    self._draw_raycast(
                        renderer,
                        node,
                    )

                continue

            # ==================================================
            # CollisionShape2D
            # ==================================================

            if isinstance(
                node,
                CollisionShape2D,
            ):
                continue

            # ==================================================
            # Body2D
            # ==================================================

            if not isinstance(
                node,
                Body2D,
            ):
                continue

            if not node.collision_enabled:
                continue

            # ==================================================
            # Area filtering
            # ==================================================

            if isinstance(
                node,
                Area2D,
            ):
                if not self.areas:
                    continue

            # ==================================================
            # Shapes
            # ==================================================

            if self.shapes:
                color = self._body_color(
                    node
                )

                for shape in (
                    node.active_collision_shapes
                ):
                    self._draw_shape(
                        renderer,
                        shape,
                        color,
                    )

            # ==================================================
            # Origin
            # ==================================================

            if self.origins:
                self._draw_origin(
                    renderer,
                    node,
                )

            # ==================================================
            # Character-specific debug
            # ==================================================

            if isinstance(
                node,
                CharacterBody2D,
            ):
                if self.velocity:
                    self._draw_velocity(
                        renderer,
                        node,
                    )

                if (
                    self.contacts
                    or self.normals
                ):
                    self._draw_collisions(
                        renderer,
                        node,
                    )

    # ==============================================================
    # Collision shape
    # ==============================================================

    def _draw_shape(
        self,
        renderer,
        shape,
        color,
    ) -> None:
        x, y, width, height = (
            shape.world_rect
        )

        self._draw_rect_outline(
            renderer,
            x,
            y,
            width,
            height,
            color=color,
        )

    # ==============================================================
    # Rectangle
    # ==============================================================

    def _draw_rect_outline(
        self,
        renderer,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        color,
    ) -> None:
        right = (
            x
            + width
        )

        bottom = (
            y
            + height
        )

        renderer.line(
            x,
            y,
            right,
            y,
            width=self.line_width,
            color=color,
        )

        renderer.line(
            right,
            y,
            right,
            bottom,
            width=self.line_width,
            color=color,
        )

        renderer.line(
            right,
            bottom,
            x,
            bottom,
            width=self.line_width,
            color=color,
        )

        renderer.line(
            x,
            bottom,
            x,
            y,
            width=self.line_width,
            color=color,
        )

    # ==============================================================
    # Origin
    # ==============================================================

    def _draw_origin(
        self,
        renderer,
        body,
    ) -> None:
        x, y = (
            body.world_position
        )

        size = (
            self.origin_size
        )

        renderer.line(
            x - size,
            y,
            x + size,
            y,
            width=1.0,
            color=self.origin_color,
        )

        renderer.line(
            x,
            y - size,
            x,
            y + size,
            width=1.0,
            color=self.origin_color,
        )

    # ==============================================================
    # Velocity
    # ==============================================================

    def _draw_velocity(
        self,
        renderer,
        body,
    ) -> None:
        velocity = (
            body.velocity
        )

        if (
            velocity.x == 0.0
            and velocity.y == 0.0
        ):
            return

        start_x, start_y = (
            body.world_position
        )

        end_x = (
            start_x
            + velocity.x
            * self.velocity_scale
        )

        end_y = (
            start_y
            + velocity.y
            * self.velocity_scale
        )

        renderer.line(
            start_x,
            start_y,
            end_x,
            end_y,
            width=2.0,
            color=self.velocity_color,
        )

    # ==============================================================
    # Body collision contacts
    # ==============================================================

    def _draw_collisions(
        self,
        renderer,
        body,
    ) -> None:
        for collision in (
            body.slide_collisions
        ):
            point_x, point_y = (
                collision.point
            )

            if self.contacts:
                self._draw_cross(
                    renderer,
                    point_x,
                    point_y,
                    self.contact_size,
                    self.contact_color,
                )

            if self.normals:
                self._draw_normal(
                    renderer,
                    point_x,
                    point_y,
                    collision.normal_x,
                    collision.normal_y,
                    length=self.normal_length,
                    color=self.normal_color,
                )

    # ==============================================================
    # RayCast2D
    # ==============================================================

    def _draw_raycast(
        self,
        renderer,
        ray,
    ) -> None:
        """
        Draw RayCast2D state.

        Ray:
            yellow when a hit exists
            gray when no hit exists

        Hit:
            red cross

        Hit normal:
            cyan arrow
        """

        origin_x, origin_y = (
            ray.ray_origin
        )

        end_x, end_y = (
            ray.ray_end
        )

        hit = (
            ray.collision
        )

        # ------------------------------------------------------
        # Origin
        # ------------------------------------------------------

        self._draw_cross(
            renderer,
            origin_x,
            origin_y,
            self.ray_origin_size,
            self.ray_color,
        )

        # ------------------------------------------------------
        # Ray line
        # ------------------------------------------------------

        if hit is None:
            renderer.line(
                origin_x,
                origin_y,
                end_x,
                end_y,
                width=1.5,
                color=self.ray_miss_color,
            )

            # End marker.
            self._draw_cross(
                renderer,
                end_x,
                end_y,
                3.0,
                self.ray_miss_color,
            )

            return

        # ------------------------------------------------------
        # Hit ray
        # ------------------------------------------------------

        hit_x, hit_y = (
            hit.point
        )

        # Visible part until collision.
        renderer.line(
            origin_x,
            origin_y,
            hit_x,
            hit_y,
            width=2.0,
            color=self.ray_color,
        )

        # Remaining configured ray range.
        renderer.line(
            hit_x,
            hit_y,
            end_x,
            end_y,
            width=1.0,
            color=self.ray_miss_color,
        )

        if not self.ray_hits:
            return

        # ------------------------------------------------------
        # Hit point
        # ------------------------------------------------------

        self._draw_cross(
            renderer,
            hit_x,
            hit_y,
            self.ray_hit_size,
            self.ray_hit_color,
        )

        # ------------------------------------------------------
        # Hit normal
        # ------------------------------------------------------

        self._draw_normal(
            renderer,
            hit_x,
            hit_y,
            hit.normal_x,
            hit.normal_y,
            length=self.ray_normal_length,
            color=self.ray_normal_color,
        )

    # ==============================================================
    # Cross helper
    # ==============================================================

    @staticmethod
    def _draw_cross(
        renderer,
        x: float,
        y: float,
        size: float,
        color,
    ) -> None:
        renderer.line(
            x - size,
            y,
            x + size,
            y,
            width=2.0,
            color=color,
        )

        renderer.line(
            x,
            y - size,
            x,
            y + size,
            width=2.0,
            color=color,
        )

    # ==============================================================
    # Normal helper
    # ==============================================================

    def _draw_normal(
        self,
        renderer,
        point_x: float,
        point_y: float,
        normal_x: float,
        normal_y: float,
        *,
        length: float,
        color,
    ) -> None:
        if (
            normal_x == 0.0
            and normal_y == 0.0
        ):
            return

        end_x = (
            point_x
            + normal_x
            * length
        )

        end_y = (
            point_y
            + normal_y
            * length
        )

        renderer.line(
            point_x,
            point_y,
            end_x,
            end_y,
            width=2.0,
            color=color,
        )

        self._draw_normal_arrow(
            renderer,
            end_x,
            end_y,
            normal_x,
            normal_y,
            color,
        )

    # ==============================================================
    # Normal arrow
    # ==============================================================

    @staticmethod
    def _draw_normal_arrow(
        renderer,
        end_x: float,
        end_y: float,
        normal_x: float,
        normal_y: float,
        color,
    ) -> None:
        size = 5.0

        # Horizontal.
        if normal_x != 0.0:
            back_x = (
                end_x
                - normal_x
                * size
            )

            renderer.line(
                end_x,
                end_y,
                back_x,
                end_y - size,
                width=2.0,
                color=color,
            )

            renderer.line(
                end_x,
                end_y,
                back_x,
                end_y + size,
                width=2.0,
                color=color,
            )

            return

        # Vertical.
        back_y = (
            end_y
            - normal_y
            * size
        )

        renderer.line(
            end_x,
            end_y,
            end_x - size,
            back_y,
            width=2.0,
            color=color,
        )

        renderer.line(
            end_x,
            end_y,
            end_x + size,
            back_y,
            width=2.0,
            color=color,
        )

    # ==============================================================
    # Colors
    # ==============================================================

    def _body_color(
        self,
        body,
    ):
        from nexora.nodes.entity import (
            Area2D,
            CharacterBody2D,
            StaticBody2D,
        )

        if isinstance(
            body,
            Area2D,
        ):
            return self.area_color

        if isinstance(
            body,
            CharacterBody2D,
        ):
            return self.character_color

        if isinstance(
            body,
            StaticBody2D,
        ):
            return self.static_color

        return self.body_color