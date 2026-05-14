"""
WSGI config for config project.

It provides the WSGI app object named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Tell WSGI servers which settings file to use before loading Django.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# App object used by standard sync deployment servers.
application = get_wsgi_application()
