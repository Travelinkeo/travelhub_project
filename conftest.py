import os

os.environ["DJANGO_TESTING"] = "True"

# root conftest.py to expose all fixtures to apps/ tests
from tests.conftest import *
