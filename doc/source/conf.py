# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
# os.environ.get()
sys.path.insert(0, os.path.abspath('../../krules-libs/krules-core'))
sys.path.insert(0, os.path.abspath('../../krules-libs/krules-subjects-k8s-storage'))


# -- Project information -----------------------------------------------------

project = 'KRules documentation'
copyright = '2021, Airspot s.r.l. Sede Legale:Via Ormea 33 10125 Torino, TO Italy C.F. e P. IVA: 12141910013'
author = 'Airspot s.r.l.'
logo = 'krules_ext_logo.png'
html_theme_options = {
    # 'logo': 'krules_ext_logo.png',
    'github_user': 'airspot-dev',
    'github_repo': 'krules-doc',
}

# The full version, including alpha/beta/rc tags
release = '0.8.5'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.napoleon', 'm2r2', "sphinx_multiversion"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}

autodoc_default_options = {
    'member-order': 'bysource',
    # 'special-members': '__init__',
    # 'undoc-members': True,
}

smv_tag_whitelist = r'^.*$'
# smv_remote_whitelist = r'^(origin|prod)$'
smv_branch_whitelist = r'^(develop).*$'

locale_dirs = ['locale/']
language = "en"
