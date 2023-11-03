from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from aisysprojserver import __version__

release = __version__

project = 'aisysprojserver'
copyright = '2022, Jan Frederik Schaefer'
author = 'Jan Frederik Schaefer'

extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.apidoc', 'sphinx.ext.todo']

apidoc_module_dir = str(Path(__file__).parent.parent.parent)
apidoc_output_dir = 'apidocs'

todo_include_todos = True

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
