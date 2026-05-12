from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
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

    def test_strategy_chart_fragment_renders_indicators(self):
        user = User.objects.create_user(username='chart-user', password='test-pass-123')
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        microsoft = Stock.objects.create(symbol='MSFT', name='Microsoft Corporation')
        seed_sample_prices(stock, days=80)
        seed_sample_prices(microsoft, days=80)
        strategy = Strategy.objects.create(
            user=user,
            stock=stock,
            name='Chart strategy',
            strategy_type=Strategy.StrategyType.MOVING_AVERAGE,
            parameters={'short_window': 5, 'long_window': 20},
            initial_balance=10000,
            position_size_percent=25,
        )
        self.client.login(username='chart-user', password='test-pass-123')

        with patch('market_data.charting.refresh_yfinance_prices', return_value=0):
            response = self.client.get(reverse('backtesting:strategy_price_chart'), {'stock': microsoft.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Line')
        self.assertContains(response, 'Candles')
        self.assertContains(response, 'EMA(50)')
        self.assertContains(response, 'SMA(20)')
        self.assertContains(response, 'RSI(14)')
        self.assertContains(response, 'name="stock"')
        self.assertContains(response, f'value="{stock.pk}"')
        self.assertContains(response, f'value="{microsoft.pk}" selected')

# Create your tests here.
