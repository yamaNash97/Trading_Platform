import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class EnsureSuperuserCommandTests(TestCase):
    def call_ensure_superuser(self, env, *args):
        output = StringIO()
        with patch.dict(os.environ, {}, clear=False):
            for key in (
                'DJANGO_SUPERUSER_USERNAME',
                'DJANGO_SUPERUSER_EMAIL',
                'DJANGO_SUPERUSER_PASSWORD',
            ):
                os.environ.pop(key, None)
            os.environ.update(env)
            call_command('ensure_superuser', *args, stdout=output)
        return output.getvalue()

    def test_creates_superuser_from_environment(self):
        self.call_ensure_superuser(
            {
                'DJANGO_SUPERUSER_USERNAME': 'admin',
                'DJANGO_SUPERUSER_EMAIL': 'admin@example.com',
                'DJANGO_SUPERUSER_PASSWORD': 'temporary-password',
            }
        )

        user = get_user_model().objects.get(username='admin')
        self.assertEqual(user.email, 'admin@example.com')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password('temporary-password'))

    def test_updates_existing_superuser_idempotently(self):
        User = get_user_model()
        User.objects.create_user(
            username='admin',
            email='old@example.com',
            password='old-password',
        )

        env = {
            'DJANGO_SUPERUSER_USERNAME': 'admin',
            'DJANGO_SUPERUSER_EMAIL': 'admin@example.com',
            'DJANGO_SUPERUSER_PASSWORD': 'new-temporary-password',
        }
        self.call_ensure_superuser(env)
        self.call_ensure_superuser(env)

        user = User.objects.get(username='admin')
        self.assertEqual(User.objects.filter(username='admin').count(), 1)
        self.assertEqual(user.email, 'admin@example.com')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password('new-temporary-password'))

    def test_updates_configured_render_admin_username(self):
        User = get_user_model()
        User.objects.create_user(
            username='AdminYama',
            email='old@example.com',
            password='old-password',
        )

        self.call_ensure_superuser(
            {
                'DJANGO_SUPERUSER_USERNAME': 'AdminYama',
                'DJANGO_SUPERUSER_EMAIL': 'admin@example.com',
                'DJANGO_SUPERUSER_PASSWORD': 'new-temporary-password',
            }
        )

        user = User.objects.get(username='AdminYama')
        self.assertEqual(user.email, 'admin@example.com')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password('new-temporary-password'))

    def test_missing_password_without_existing_user_fails(self):
        with self.assertRaises(CommandError):
            self.call_ensure_superuser(
                {
                    'DJANGO_SUPERUSER_USERNAME': 'AdminYama',
                    'DJANGO_SUPERUSER_EMAIL': 'admin@example.com',
                }
            )

    def test_skip_if_missing_password_does_not_create_user(self):
        output = self.call_ensure_superuser(
            {
                'DJANGO_SUPERUSER_USERNAME': 'admin',
                'DJANGO_SUPERUSER_EMAIL': 'admin@example.com',
            },
            '--skip-if-missing',
        )

        self.assertIn('Skipping', output)
        self.assertFalse(get_user_model().objects.filter(username='admin').exists())
