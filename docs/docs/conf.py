"""
    Configuration specific to project
"""
import sys
import os

this_dir = os.path.abspath(os.path.dirname(__file__))
docs_dir = os.path.join(this_dir, '..')
sys.path.append(docs_dir)
from support.conf import *

copyright = u'2014, Stephen Moore'
project = u'db_backup'

version = '0.1'
release = '0.1'
