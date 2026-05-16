from unittest.mock import patch
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from market_data.models import Stock
from market_data.services import seed_sample_prices
from portfolio.models import PortfolioHolding

from .models import Order
from .services import execute_order, get_or_create_account


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
