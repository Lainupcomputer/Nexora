"""Backward-compatible import facade for the shared editor UI package.

New editor code should import widgets from :mod:`nexora.editor.ui`.  This
module remains intentionally tiny so integrations using the old import path
continue to work while the UI implementation has a single home.
"""

from .ui import *  # noqa: F401,F403
from .ui import __all__
