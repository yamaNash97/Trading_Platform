from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from market_data.models import Stock

from .forms import StrategyForm
from .models import Strategy


User = get_user_model()


class StrategyFormTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        self.common_data = {
            'stock': self.stock.pk,
            'name': 'Test strategy',
            'initial_balance': '10000',
            'position_size_percent': '25',
            'stop_loss_percent': '8',
            'take_profit_percent': '15',
            'is_active': 'on',
        }

    def test_rsi_strategy_does_not_require_moving_average_fields(self):
        form = StrategyForm(
            data={
                **self.common_data,
                'strategy_type': Strategy.StrategyType.RSI,
                'rsi_period': '14',
                'rsi_buy_threshold': '30',
                'rsi_sell_threshold': '70',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        strategy = form.save(commit=False)
        self.assertEqual(strategy.parameters['short_window'], 20)
        self.assertEqual(strategy.parameters['long_window'], 50)

    def test_moving_average_strategy_does_not_require_rsi_fields(self):
        form = StrategyForm(
            data={
                **self.common_data,
                'strategy_type': Strategy.StrategyType.MOVING_AVERAGE,
                'short_window': '10',
                'long_window': '30',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        strategy = form.save(commit=False)
        self.assertEqual(strategy.parameters['rsi_period'], 14)
        self.assertEqual(strategy.parameters['rsi_buy_threshold'], 30)
        self.assertEqual(strategy.parameters['rsi_sell_threshold'], 70)

    def test_combined_strategy_requires_both_indicator_groups(self):
        form = StrategyForm(
            data={
                **self.common_data,
                'strategy_type': Strategy.StrategyType.COMBINED,
                'short_window': '10',
                'long_window': '30',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn('rsi_period', form.errors)
        self.assertIn('rsi_buy_threshold', form.errors)
        self.assertIn('rsi_sell_threshold', form.errors)


class StrategyCreateViewTests(TestCase):
    def test_form_marks_indicator_groups_for_conditional_display(self):
        user = User.objects.create_user(username='strategy-user', password='test-pass-123')
        self.client.force_login(user)

        response = self.client.get(reverse('strategies:strategy_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-strategy-form')
        self.assertContains(response, 'data-strategy-fields="moving_average"', count=2)
        self.assertContains(response, 'data-strategy-fields="rsi"', count=3)
