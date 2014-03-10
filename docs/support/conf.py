"""
    Options for sphinx
    Add project specific options to conf.py in the root folder
"""
import cloud_sptheme
import sys, os

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

# Add _ext and support folders to sys.path
this_dir = os.path.abspath(os.path.dirname(__file__))
docs_dir = os.path.join(this_dir, '..', 'docs')
project_dir = os.path.join(this_dir, '..', '..')

ext_dir = os.path.join(this_dir, 'ext')
build_dir = os.path.join(this_dir, "build")
theme_dir = os.path.join(this_dir, "theme")
rtd_build_dir = os.path.join(docs_dir, '_build')

sys.path.extend([this_dir, ext_dir, project_dir])

html_theme_path = [theme_dir, cloud_sptheme.get_theme_dir()]
exclude_patterns = [build_dir, rtd_build_dir]

master_doc = 'index'
source_suffix = '.rst'

html_theme = 'navcloud'
html_use_index = False
pygments_style = 'pastie'
