import os
import sys

# Ensure the root directory is on the path so 'tests' can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tests.conftest import *  # noqa: F403
