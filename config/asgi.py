"""
ASGI config for config project.

It provides the ASGI app object named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Tell ASGI servers which settings file to use before loading Django.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# App object used by async deployment servers.
application = get_asgi_application()
