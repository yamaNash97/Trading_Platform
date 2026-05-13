from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from market_data.models import PriceData, Stock
from market_data.services import seed_sample_prices
from strategies.models import Strategy

from .models import BacktestResult, BacktestTrade
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
            equity_curve=[
                {'date': (today - timedelta(days=1)).isoformat(), 'equity': '10000.00'},
                {'date': today.isoformat(), 'equity': '126108127.01'},
            ],
        )
        self.client.login(username='large-return-user', password='test-pass-123')

        response = self.client.get(reverse('backtesting:backtest_detail', kwargs={'pk': result.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1260981.27%')
        self.assertContains(response, 'id="equity-curve-chart"')
        self.assertContains(response, 'id="equity-curve-data"')

    def test_backtest_uses_real_prices_instead_of_sample_when_available(self):
        user = User.objects.create_user(username='real-price-user', password='test-pass-123')
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        today = timezone.now().date()
        for offset in range(5):
            PriceData.objects.create(
                stock=stock,
                timestamp=timezone.make_aware(datetime.combine(today - timedelta(days=9 - offset), time.min)),
                open_price='100.0000',
                high_price='101.0000',
                low_price='99.0000',
                close_price='100.0000',
                volume=1000,
                source='sample',
            )
        for offset in range(4):
            PriceData.objects.create(
                stock=stock,
                timestamp=timezone.make_aware(datetime.combine(today - timedelta(days=4 - offset), time.min)),
                open_price='200.0000',
                high_price='201.0000',
                low_price='199.0000',
                close_price='200.0000',
                volume=1000,
                source='yfinance',
            )
        strategy = Strategy.objects.create(
            user=user,
            stock=stock,
            name='Real only strategy',
            strategy_type=Strategy.StrategyType.MOVING_AVERAGE,
            parameters={'short_window': 2, 'long_window': 5},
            initial_balance=10000,
            position_size_percent=50,
        )

        with self.assertRaisesMessage(ValueError, 'Not enough price history'):
            run_backtest(user, strategy, today - timedelta(days=10), today)

    def test_backtest_records_actual_price_range_used(self):
        user = User.objects.create_user(username='actual-range-user', password='test-pass-123')
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        today = timezone.now().date()
        for offset in range(6):
            PriceData.objects.create(
                stock=stock,
                timestamp=timezone.make_aware(datetime.combine(today - timedelta(days=11 - offset), time.min)),
                open_price='100.0000',
                high_price='101.0000',
                low_price='99.0000',
                close_price='100.0000',
                volume=1000,
                source='sample',
            )
        for offset in range(5):
            PriceData.objects.create(
                stock=stock,
                timestamp=timezone.make_aware(datetime.combine(today - timedelta(days=4 - offset), time.min)),
                open_price='200.0000',
                high_price='201.0000',
                low_price='199.0000',
                close_price='200.0000',
                volume=1000,
                source='yfinance',
            )
        strategy = Strategy.objects.create(
            user=user,
            stock=stock,
            name='Actual range strategy',
            strategy_type=Strategy.StrategyType.MOVING_AVERAGE,
            parameters={'short_window': 2, 'long_window': 5},
            initial_balance=10000,
            position_size_percent=50,
        )

        result = run_backtest(user, strategy, today - timedelta(days=12), today)

        self.assertEqual(result.start_date, today - timedelta(days=4))
        self.assertEqual(result.end_date, today)
        self.assertEqual(len(result.equity_curve), 5)

    def test_backtest_detail_warns_about_mixed_source_saved_trades(self):
        user = User.objects.create_user(username='mixed-source-user', password='test-pass-123')
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        strategy = Strategy.objects.create(
            user=user,
            stock=stock,
            name='Mixed source strategy',
            strategy_type=Strategy.StrategyType.MOVING_AVERAGE,
            parameters={'short_window': 2, 'long_window': 5},
            initial_balance=10000,
            position_size_percent=50,
        )
        today = timezone.now().date()
        entry_time = timezone.make_aware(datetime.combine(today - timedelta(days=1), time.min))
        exit_time = timezone.make_aware(datetime.combine(today, time.min))
        PriceData.objects.create(
            stock=stock,
            timestamp=entry_time,
            open_price='100.0000',
            high_price='101.0000',
            low_price='99.0000',
            close_price='100.0000',
            volume=1000,
            source='sample',
        )
        PriceData.objects.create(
            stock=stock,
            timestamp=exit_time,
            open_price='200.0000',
            high_price='201.0000',
            low_price='199.0000',
            close_price='200.0000',
            volume=1000,
            source='yfinance',
        )
        result = BacktestResult.objects.create(
            user=user,
            strategy=strategy,
            stock=stock,
            start_date=today - timedelta(days=1),
            end_date=today,
            initial_balance=Decimal('10000.00'),
            final_balance=Decimal('10100.00'),
            total_return=Decimal('1.00'),
            max_drawdown=Decimal('0.00'),
            number_of_trades=1,
            win_loss_ratio=Decimal('1.00'),
        )
        BacktestTrade.objects.create(
            result=result,
            entered_at=entry_time,
            exited_at=exit_time,
            entry_price=Decimal('100.0000'),
            exit_price=Decimal('200.0000'),
            quantity=Decimal('1.000000'),
            pnl=Decimal('100.00'),
            exit_reason='signal',
        )
        self.client.login(username='mixed-source-user', password='test-pass-123')

        response = self.client.get(reverse('backtesting:backtest_detail', kwargs={'pk': result.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'mixed sample prices with live market prices')

    def test_result_chart_is_locked_to_backtest_history(self):
        user = User.objects.create_user(username='result-chart-user', password='test-pass-123')
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        microsoft = Stock.objects.create(symbol='MSFT', name='Microsoft Corporation')
        seed_sample_prices(stock, days=30)
        seed_sample_prices(microsoft, days=30)
        strategy = Strategy.objects.create(
            user=user,
            stock=stock,
            name='Result chart strategy',
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
            start_date=today - timedelta(days=60),
            end_date=today,
            initial_balance=Decimal('10000.00'),
            final_balance=Decimal('10100.00'),
            total_return=Decimal('1.00'),
            max_drawdown=Decimal('0.00'),
            number_of_trades=0,
            win_loss_ratio=Decimal('0.00'),
        )
        self.client.login(username='result-chart-user', password='test-pass-123')

        with patch('market_data.charting.refresh_yfinance_prices') as refresh_prices:
            response = self.client.get(
                reverse('backtesting:result_price_chart', kwargs={'pk': result.pk}),
                {'stock': microsoft.pk, 'refresh': '1'},
            )

        self.assertEqual(response.status_code, 200)
        refresh_prices.assert_not_called()
        self.assertContains(response, 'data-live-refresh="0"')
        self.assertContains(response, 'AAPL')
        self.assertNotContains(response, 'name="stock"')

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
        self.assertContains(response, 'RSI(14)')
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
