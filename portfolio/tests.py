from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class DashboardViewTests(TestCase):
    def test_landing_page_renders_join_button_to_login(self):
        response = self.client.get(reverse('portfolio:landing'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Join Us!')
        self.assertContains(response, reverse('login'))

    def test_login_and_logout_route_flow(self):
        User.objects.create_user(username='viewer', password='test-pass-123')

        login_page = self.client.get(reverse('login'))
        self.assertEqual(login_page.status_code, 200)
        self.assertContains(login_page, 'Sign in')
        self.assertNotContains(login_page, 'Trading Simulator')

        login_response = self.client.post(
            reverse('login'),
            {'username': 'viewer', 'password': 'test-pass-123'},
        )
        self.assertRedirects(login_response, reverse('portfolio:dashboard'))

        logout_response = self.client.post(reverse('logout'))
        self.assertRedirects(logout_response, reverse('portfolio:landing'))

    def test_dashboard_renders_for_logged_in_user(self):
        user = User.objects.create_user(username='viewer', password='test-pass-123')
        self.client.login(username='viewer', password='test-pass-123')

        response = self.client.get(reverse('portfolio:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Portfolio Dashboard')

# Create your tests here.
