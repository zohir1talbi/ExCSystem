"""Top level loading for django application"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ExCSystem.settings")

application = get_wsgi_application()
