from pathlib import Path
import sys

# Add the project root to sys.path so autodoc can import nexora.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

project = "Nexora Engine"
copyright = "2026, Nexora Team"
author = "Nexora Team"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

templates_path = ["_templates"]
exclude_patterns = []

language = "en"

html_theme = "furo"
html_static_path = ["_static"]