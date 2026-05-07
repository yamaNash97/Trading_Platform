from django.test import TestCase

from .models import Stock
from .services import seed_sample_prices


class MarketDataTests(TestCase):
    def test_sample_price_seed_is_idempotent(self):
        stock = Stock.objects.create(symbol='msft', name='Microsoft Corporation')

        created_first = seed_sample_prices(stock, days=30)
        created_second = seed_sample_prices(stock, days=30)

        self.assertEqual(created_first, 30)
        self.assertEqual(created_second, 0)
        self.assertEqual(stock.price_data.count(), 30)
        self.assertEqual(stock.symbol, 'MSFT')

# Create your tests here.
