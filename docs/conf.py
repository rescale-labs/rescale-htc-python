# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from sphinx_pyproject import SphinxConfig

# Fetch author and release etc from pyproject.toml
config = SphinxConfig("../pyproject.toml", globalns=globals())

project = 'rescalehtc'
copyright = 'MIT License'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Extensions for python autodoc and section labeling
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.autosectionlabel']

# Make sure the target is unique
autosectionlabel_prefix_document = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Find the python source code
import sys
sys.path.insert(0, "../src/")

# Order members by source, not alphabetical
autodoc_member_order = 'bysource'

# Document __init__ constructs too
autoclass_content = 'both'

# Warn on broken references in docstrings etc
nitpicky = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
