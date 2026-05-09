from unittest.mock import patch

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

        order = Order(user=user, stock=stock, order_type=Order.OrderType.BUY, quantity=1)
        execute_order(order)

        account.refresh_from_db()
        holding = PortfolioHolding.objects.get(user=user, stock=stock)
        self.assertEqual(order.status, Order.Status.FILLED)
        self.assertEqual(holding.quantity, 1)
        self.assertLess(account.balance, account.starting_balance)

    def test_price_chart_fragment_renders_indicators(self):
        user = User.objects.create_user(username='paper-chart', password='test-pass-123')
        stock = Stock.objects.create(symbol='TSLA', name='Tesla Inc.')
        seed_sample_prices(stock, days=80)
        self.client.login(username='paper-chart', password='test-pass-123')

        with patch('market_data.charting.refresh_yfinance_prices', return_value=0):
            response = self.client.get(reverse('paper_trading:price_chart'), {'stock': stock.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Line')
        self.assertContains(response, 'Candles')
        self.assertContains(response, 'EMA(50)')
        self.assertContains(response, 'SMA(20)')
        self.assertContains(response, 'RSI(14)')

# Create your tests here.
