"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Point ASGI servers at the project settings module before loading Django.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Module-level callable used by async-capable deployment servers.
application = get_asgi_application()
