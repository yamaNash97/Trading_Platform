from unittest.mock import patch
from decimal import Decimal
from datetime import timezone as datetime_timezone

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from market_data.models import PriceData, Stock
from market_data.services import seed_sample_prices
from portfolio.models import PortfolioHolding

from .models import Order
from .services import execute_order, get_or_create_account, open_trade_rows


class PaperTradingTests(TestCase):
    def test_buy_order_updates_cash_and_holding(self):
        user = User.objects.create_user(username='paper', password='test-pass-123')
        stock = Stock.objects.create(symbol='TSLA', name='Tesla Inc.')
        seed_sample_prices(stock, days=10)
        account = get_or_create_account(user)

        order = Order(user=user, stock=stock, order_type=Order.OrderType.BUY, quantity=Decimal('1'))
        execute_order(order)

        account.refresh_from_db()
        holding = PortfolioHolding.objects.get(user=user, stock=stock)
        self.assertEqual(order.status, Order.Status.FILLED)
        self.assertEqual(holding.quantity, 1)
        self.assertLess(account.balance, account.starting_balance)

    def test_exit_trade_sells_full_position_and_updates_cash_with_realized_pnl(self):
        user = User.objects.create_user(username='paper-exit', password='test-pass-123')
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        seed_sample_prices(stock, days=10)
        account = get_or_create_account(user)
        self.client.login(username='paper-exit', password='test-pass-123')

        buy_order = Order(user=user, stock=stock, order_type=Order.OrderType.BUY, quantity=Decimal('2'))
        execute_order(buy_order)
        latest = stock.price_data.order_by('-timestamp').first()
        latest.close_price = buy_order.price + Decimal('10.0000')
        latest.open_price = latest.close_price
        latest.high_price = latest.close_price
        latest.low_price = latest.close_price
        latest.save()

        response = self.client.post(reverse('paper_trading:exit_trade', args=[stock.pk]), follow=True)

        account.refresh_from_db()
        holding = PortfolioHolding.objects.get(user=user, stock=stock)
        sell_order = Order.objects.filter(user=user, stock=stock, order_type=Order.OrderType.SELL).first()
        realized_pnl = (sell_order.price - buy_order.price) * buy_order.quantity
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sell_order.status, Order.Status.FILLED)
        self.assertEqual(holding.quantity, 0)
        self.assertEqual(account.balance, account.starting_balance + realized_pnl)
        self.assertContains(response, 'You made $20.00')

    def test_open_trades_fragment_can_refresh_live_prices(self):
        user = User.objects.create_user(username='paper-open', password='test-pass-123')
        stock = Stock.objects.create(symbol='MSFT', name='Microsoft Corporation')
        seed_sample_prices(stock, days=10)
        self.client.login(username='paper-open', password='test-pass-123')

        order = Order(user=user, stock=stock, order_type=Order.OrderType.BUY, quantity=Decimal('1'))
        execute_order(order)
        refreshed_price = order.price + Decimal('25.0000')

        def fake_refresh(refreshed_stock):
            latest = refreshed_stock.price_data.order_by('-timestamp').first()
            latest.close_price = refreshed_price
            latest.open_price = refreshed_price
            latest.high_price = refreshed_price
            latest.low_price = refreshed_price
            latest.source = 'yfinance'
            latest.save()
            return 0

        with patch('market_data.charting.refresh_yfinance_prices', side_effect=fake_refresh) as refresh:
            response = self.client.get(reverse('paper_trading:open_trades'), {'refresh': '1'})

        self.assertEqual(response.status_code, 200)
        refresh.assert_called_once_with(stock)
        self.assertContains(response, 'Open trades')
        self.assertContains(response, f'${refreshed_price:.2f}')
        self.assertContains(response, '$25.00')
        self.assertContains(response, 'Exit')

    def test_open_trade_rows_prefer_live_prices_over_newer_sample_rows(self):
        user = User.objects.create_user(username='paper-live-price', password='test-pass-123')
        stock = Stock.objects.create(symbol='NVDA', name='NVIDIA Corporation')
        PriceData.objects.create(
            stock=stock,
            timestamp=timezone.datetime(2026, 5, 8, 13, 30, tzinfo=datetime_timezone.utc),
            open_price='120.0000',
            high_price='121.0000',
            low_price='119.0000',
            close_price='120.0000',
            volume=1000000,
            source='yfinance',
        )
        PriceData.objects.create(
            stock=stock,
            timestamp=timezone.datetime(2026, 5, 9, tzinfo=datetime_timezone.utc),
            open_price='80.0000',
            high_price='81.0000',
            low_price='79.0000',
            close_price='80.0000',
            volume=1000,
            source='sample',
        )
        PortfolioHolding.objects.create(
            user=user,
            stock=stock,
            quantity=Decimal('2'),
            average_buy_price=Decimal('100.0000'),
        )

        rows, warnings = open_trade_rows(user)

        self.assertEqual(warnings, [])
        self.assertEqual(rows[0]['current_price'], Decimal('120.0000'))
        self.assertEqual(rows[0]['unrealized_pnl'], Decimal('40.0000000000'))

    def test_paper_account_open_trades_auto_refreshes_values(self):
        user = User.objects.create_user(username='paper-auto-refresh', password='test-pass-123')
        stock = Stock.objects.create(symbol='TSLA', name='Tesla Inc.')
        seed_sample_prices(stock, days=10)
        self.client.login(username='paper-auto-refresh', password='test-pass-123')

        order = Order(user=user, stock=stock, order_type=Order.OrderType.BUY, quantity=Decimal('1'))
        execute_order(order)

        response = self.client.get(reverse('paper_trading:paper_account'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('paper_trading:open_trades') + '?refresh=1')
        self.assertContains(response, 'hx-trigger="load"')
        self.assertContains(response, 'hx-trigger="every 300s"')

    def test_price_chart_fragment_renders_chart_controls(self):
        user = User.objects.create_user(username='paper-chart', password='test-pass-123')
        stock = Stock.objects.create(symbol='TSLA', name='Tesla Inc.')
        microsoft = Stock.objects.create(symbol='MSFT', name='Microsoft Corporation')
        seed_sample_prices(stock, days=80)
        seed_sample_prices(microsoft, days=80)
        self.client.login(username='paper-chart', password='test-pass-123')

        with patch('market_data.charting.refresh_yfinance_prices', return_value=0):
            response = self.client.get(reverse('paper_trading:price_chart'), {'stock': microsoft.pk})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Candles')
        self.assertNotContains(response, 'Bars')
        self.assertNotContains(response, 'data-chart-view')
        self.assertContains(response, 'EMA(50)')
        self.assertContains(response, 'RSI(14)')
        self.assertContains(response, 'name="stock"')
        self.assertContains(response, f'value="{stock.pk}"')
        self.assertContains(response, f'value="{microsoft.pk}" selected')
