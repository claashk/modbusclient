# Configuration file for the Sphinx documentation builder.
#
# For full list of built-in documentation values, see:
# http://www.sphinx-doc.org/en/master/config

import modbusclient

# -- Project information -----------------------------------------------------

project = 'modbusclient'
copyright = '2025, claashk'
author = 'claashk'

release = modbusclient.__version__
version = ".".join(release.split('.')[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

needs_sphinx = '8.1'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
]

templates_path = ['_templates']
master_doc = 'index'
exclude_patterns = []
language = "en"
pygments_style = 'sphinx'
source_suffix = {'.rst': 'restructuredtext'}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'modbusclientdoc'


# -- Options for LaTeX output ------------------------------------------------

latex_elements = {}
latex_documents = [
    (master_doc, 'modbusclient.tex', 'modbusclient Documentation',
     'claashk', 'manual'),
]

# -- Options for manual page output ------------------------------------------
man_pages = [
    (master_doc, 'modbusclient', 'modbusclient Documentation', [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------
texinfo_documents = [
    (master_doc, 'modbusclient', 'modbusclient Documentation',
     author, 'modbusclient', 'One line description of project.',
     'Miscellaneous'),
]

# -- Options for intersphinx extension ---------------------------------------
intersphinx_mapping = {'https://docs.python.org/3': None}
