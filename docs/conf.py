#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# documentation build configuration file, created by
# sphinx-quickstart on Tue Jun 13 22:58:12 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import alabaster
import os
import sys
from collections import OrderedDict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import gentools  # noqa

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.intersphinx',
              'sphinx.ext.napoleon',
              'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'gentools'
copyright = gentools.__copyright__
author = gentools.__author__

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = gentools.__version__
# The full version, including alpha/beta/rc tags.
release = gentools.__version__

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'


# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    # Set the name of the project to appear in the sidebar
    'description': gentools.__description__,
    'description_font_style': 'italic',
    'github_user': 'ariebovenberg',
    'github_repo': 'gentools',
    'github_banner': True,
    'github_type': 'star',
    'warn_bg': '#FFC',
    'warn_border': '#EEE',
    'code_font_size': '0.8em',
}


html_sidebars = {
    '**': ['about.html',
           'localtoc.html', 'relations.html', 'searchbox.html']
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}
