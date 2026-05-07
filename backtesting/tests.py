from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from market_data.models import Stock
from market_data.services import seed_sample_prices
from strategies.models import Strategy

from .services import run_backtest


class BacktestEngineTests(TestCase):
    def test_backtest_creates_result_with_equity_curve(self):
        user = User.objects.create_user(username='trader', password='test-pass-123')
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        seed_sample_prices(stock, days=120)
        strategy = Strategy.objects.create(
            user=user,
            stock=stock,
            name='MA test',
            strategy_type=Strategy.StrategyType.MOVING_AVERAGE,
            parameters={'short_window': 5, 'long_window': 20, 'rsi_period': 14, 'rsi_buy_threshold': 30, 'rsi_sell_threshold': 70},
            initial_balance=10000,
            position_size_percent=50,
        )

        end_date = timezone.now().date()
        result = run_backtest(user, strategy, end_date - timedelta(days=180), end_date)

        self.assertEqual(result.user, user)
        self.assertGreater(len(result.equity_curve), 0)
        self.assertGreaterEqual(result.number_of_trades, 0)

# Create your tests here.
