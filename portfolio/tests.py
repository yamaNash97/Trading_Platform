from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class DashboardViewTests(TestCase):
    def test_dashboard_renders_for_logged_in_user(self):
        user = User.objects.create_user(username='viewer', password='test-pass-123')
        self.client.login(username='viewer', password='test-pass-123')

        response = self.client.get(reverse('portfolio:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Portfolio Dashboard')

# Create your tests here.
