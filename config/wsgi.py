"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Point WSGI servers at the project settings module before loading Django.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Module-level callable used by traditional synchronous deployment servers.
application = get_wsgi_application()
