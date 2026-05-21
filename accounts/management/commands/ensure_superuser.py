import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


DEFAULT_USERNAME = 'admin'
DEFAULT_EMAIL = 'yaman.nashawati@gmail.com'


class Command(BaseCommand):
    help = 'Create or update the configured Django superuser.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-if-missing',
            action='store_true',
            help='Exit successfully when DJANGO_SUPERUSER_PASSWORD is missing.',
        )

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', DEFAULT_USERNAME).strip()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', DEFAULT_EMAIL).strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        skip_if_missing = options['skip_if_missing']

        if not username:
            raise CommandError('DJANGO_SUPERUSER_USERNAME cannot be empty.')

        User = get_user_model()
        lookup = {User.USERNAME_FIELD: username}
        user = User._default_manager.filter(**lookup).first()

        if not password and user is None:
            message = 'DJANGO_SUPERUSER_PASSWORD is required to create the superuser.'
            if skip_if_missing:
                self.stdout.write(self.style.WARNING(f'{message} Skipping.'))
                return
            raise CommandError(message)

        created = user is None
        if created:
            user = User(**lookup)

        if hasattr(user, 'email'):
            user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True

        if password:
            user.set_password(password)

        user.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} superuser {username!r}.'))
