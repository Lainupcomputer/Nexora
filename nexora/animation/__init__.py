from typing import TYPE_CHECKING

from nexora.animation.clip import AnimationClip, AnimationEvent, AnimationFrame
from nexora.animation.animator import Animator
from nexora.animation.animation_set import AnimationSet
from nexora.animation.state_machine import AnimationStateMachine, AnimationTransition
from nexora.animation.fsm import State, StateMachine, StateTransition, TransitionCondition
from nexora.animation.tween import (
    EASINGS,
    EaseFunction,
    Tween,
    TweenManager,
    TweenSequence,
    resolve_easing,
)

if TYPE_CHECKING:
    from nexora.animation.player import AnimationPlayer


def __getattr__(name: str):
    """Lazily expose node-dependent animation types.

    AnimationPlayer subclasses Node. Importing it eagerly from this package
    creates a cycle when low-level animation helpers such as tween are loaded
    while the nodes package is still being initialised.
    """
    if name == "AnimationPlayer":
        from nexora.animation.player import AnimationPlayer

        globals()[name] = AnimationPlayer
        return AnimationPlayer

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AnimationFrame",
    "AnimationEvent",
    "AnimationClip",
    "Animator",
    "AnimationSet",
    "AnimationPlayer",
    "AnimationStateMachine",
    "AnimationTransition",
    "State",
    "StateMachine",
    "StateTransition",
    "TransitionCondition",
    "EASINGS",
    "EaseFunction",
    "Tween",
    "TweenManager",
    "TweenSequence",
    "resolve_easing",
]
