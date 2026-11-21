"""Copy this into the WSGI file linked from PythonAnywhere's Web tab.

Replace the username and create a private .env file in the project directory.
"""

import sys

PROJECT_DIR = "/home/YOUR_USERNAME/skillswap_back"
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from config.wsgi import application
