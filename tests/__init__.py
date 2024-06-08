import os
import sys
from . import api_flask_mock

# Add the library path, so tests (and test frameworks) can
# pick up the library under test.
sys.path.insert(0, f"{os.path.dirname(os.path.abspath(__file__))}/../src")
sys.path.insert(0, f"{os.path.dirname(os.path.abspath(__file__))}/../tests")
