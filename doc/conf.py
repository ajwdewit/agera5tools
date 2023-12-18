# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys, os
import datetime

# add agera5tools to the python path
pwd = os.path.dirname(__file__)
path = os.path.abspath(os.path.join(pwd, ".."))
sys.path.append(path)
version_full = __import__("agera5tools").__version__
version_short = version_full[0:3]

project = 'AgERA5tools'
author = 'Allard de Wit'
this_year = datetime.date.today().year
copyright = '%s, %s' % (this_year, author)


# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = version_full
# The full version, including alpha/beta/rc tags.
release = version_short

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage',
              'sphinx.ext.mathjax', 'sphinx.ext.viewcode', 'sphinx.ext.autosectionlabel',
              'sphinx_rtd_theme']
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']


