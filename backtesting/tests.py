from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from market_data.models import Stock
from market_data.services import seed_sample_prices
from strategies.models import Strategy

from .models import BacktestResult
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
        for trade in result.trades.all():
            self.assertGreaterEqual(trade.quantity.as_tuple().exponent, -6)

    def test_backtest_detail_renders_large_total_return(self):
        user = User.objects.create_user(username='large-return-user', password='test-pass-123')
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        strategy = Strategy.objects.create(
            user=user,
            stock=stock,
            name='Large return strategy',
            strategy_type=Strategy.StrategyType.MOVING_AVERAGE,
            parameters={'short_window': 5, 'long_window': 20},
            initial_balance=10000,
            position_size_percent=50,
        )
        today = timezone.now().date()
        result = BacktestResult.objects.create(
            user=user,
            strategy=strategy,
            stock=stock,
            start_date=today - timedelta(days=30),
            end_date=today,
            initial_balance=Decimal('10000.00'),
            final_balance=Decimal('126108127.01'),
            total_return=Decimal('1260981.27'),
            max_drawdown=Decimal('3.90'),
            number_of_trades=8,
            win_loss_ratio=Decimal('3.00'),
        )
        self.client.login(username='large-return-user', password='test-pass-123')

        response = self.client.get(reverse('backtesting:backtest_detail', kwargs={'pk': result.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1260981.27%')

    def test_strategy_chart_fragment_renders_chart_controls(self):
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
        self.assertNotContains(response, 'Candles')
        self.assertNotContains(response, 'Bars')
        self.assertNotContains(response, 'data-chart-view')
        self.assertContains(response, 'EMA(50)')
        self.assertNotContains(response, 'RSI(14)')
        self.assertContains(response, 'name="stock"')
        self.assertContains(response, f'value="{stock.pk}"')
        self.assertContains(response, f'value="{microsoft.pk}" selected')
        self.assertContains(response, '300s')
        self.assertNotContains(response, '{{ interval }}')

    def test_strategy_chart_fragment_handles_blank_strategy(self):
        user = User.objects.create_user(username='blank-strategy-user', password='test-pass-123')
        self.client.login(username='blank-strategy-user', password='test-pass-123')

        response = self.client.get(reverse('backtesting:strategy_price_chart'), {'strategy': ''})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No chart data yet')
        self.assertContains(response, 'Add a stock or create an active strategy to load a chart.')
