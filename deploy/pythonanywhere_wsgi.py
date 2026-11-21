"""Copy this into the WSGI file linked from PythonAnywhere's Web tab.

Replace the username, frontend origin and secret before using it.
"""

import os
import sys

PROJECT_DIR = "/home/YOUR_USERNAME/skillswap_back"
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DEBUG"] = "0"
os.environ["DJANGO_ALLOWED_HOSTS"] = "YOUR_USERNAME.pythonanywhere.com"
os.environ["CORS_ALLOWED_ORIGINS"] = "https://YOUR_FRONTEND_DOMAIN"
os.environ["DJANGO_SECRET_KEY"] = "REPLACE_WITH_A_LONG_RANDOM_SECRET"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
