# -- Project information -----------------------------------------------------
import importlib.metadata

metadata = importlib.metadata.metadata("gentools")

project = metadata["Name"]
author = metadata["Author"]
version = metadata["Version"]
release = metadata["Version"]


# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
templates_path = ["_templates"]
source_suffix = ".rst"

master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output ----------------------------------------------

autodoc_member_order = "bysource"
html_theme = "furo"
highlight_language = "python3"
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
