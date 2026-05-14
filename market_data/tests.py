from datetime import timezone as datetime_timezone
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .charting import chart_context
from .models import PriceData, Stock
from .services import (
    COMMODITY_DEFINITIONS,
    AlphaVantageClient,
    import_alpha_vantage_commodity,
    seed_sample_prices,
)


class MarketDataTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='market-user', password='test-pass-123')

    def test_sample_price_seed_is_idempotent(self):
        stock = Stock.objects.create(symbol='msft', name='Microsoft Corporation')

        created_first = seed_sample_prices(stock, days=30)
        created_second = seed_sample_prices(stock, days=30)

        self.assertEqual(created_first, 30)
        self.assertEqual(created_second, 0)
        self.assertEqual(stock.price_data.count(), 30)
        self.assertEqual(stock.symbol, 'MSFT')

    def test_commodity_import_normalizes_close_only_series(self):
        class FakeClient:
            def commodity_history(self, definition):
                return [{'date': '2026-05-01', 'price': '2300.25'}]

        original_client = __import__('market_data.services', fromlist=['AlphaVantageClient']).AlphaVantageClient
        services = __import__('market_data.services', fromlist=['AlphaVantageClient'])
        services.AlphaVantageClient = lambda: FakeClient()
        try:
            stock, imported = import_alpha_vantage_commodity('GOLD')
        finally:
            services.AlphaVantageClient = original_client

        price = stock.price_data.get()
        self.assertEqual(imported, 1)
        self.assertEqual(stock.name, COMMODITY_DEFINITIONS['GOLD']['name'])
        self.assertEqual(price.open_price, price.close_price)
        self.assertEqual(price.volume, 0)

    def test_alpha_vantage_daily_client_uses_free_compact_output(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'Time Series (Daily)': {
                '2026-05-14': {
                    '1. open': '101.00',
                    '2. high': '103.00',
                    '3. low': '100.00',
                    '4. close': '102.00',
                    '5. volume': '1000',
                },
            },
        }

        with patch('market_data.services.requests.get', return_value=response) as get:
            series = AlphaVantageClient(api_key='demo-key').daily('AAPL')

        self.assertEqual(len(series), 1)
        self.assertEqual(get.call_args.kwargs['params']['outputsize'], 'compact')

    def test_commodity_import_accepts_yahoo_gold_futures_alias_for_existing_stock(self):
        stock = Stock.objects.create(symbol='GC=F', name='Gold Futures')

        class FakeClient:
            def commodity_history(self, definition):
                return [{'date': '2026-05-01', 'price': '2300.25'}]

        original_client = __import__('market_data.services', fromlist=['AlphaVantageClient']).AlphaVantageClient
        services = __import__('market_data.services', fromlist=['AlphaVantageClient'])
        services.AlphaVantageClient = lambda: FakeClient()
        try:
            returned_stock, imported = import_alpha_vantage_commodity('GC=F', stock=stock)
        finally:
            services.AlphaVantageClient = original_client

        price = stock.price_data.get()
        self.assertEqual(returned_stock, stock)
        self.assertEqual(imported, 1)
        self.assertEqual(price.source, 'alpha_vantage_gold_silver_history')

    def test_alpha_vantage_refresh_routes_supported_commodity_aliases(self):
        stock = Stock.objects.create(symbol='GC=F', name='Gold Futures')
        self.client.login(username='market-user', password='test-pass-123')

        with patch('market_data.views.import_alpha_vantage_commodity', return_value=(stock, 3)) as commodity_import:
            with patch('market_data.views.import_alpha_vantage_daily') as daily_import:
                response = self.client.get(reverse('market_data:refresh_alpha_vantage', args=[stock.pk]), follow=True)

        commodity_import.assert_called_once_with('GC=F', stock=stock)
        daily_import.assert_not_called()
        self.assertContains(response, '3 new free Alpha Vantage commodity rows imported for GC=F.')

    def test_stock_chart_renders_stock_dropdown(self):
        apple = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        microsoft = Stock.objects.create(symbol='MSFT', name='Microsoft Corporation')
        seed_sample_prices(apple, days=30)
        seed_sample_prices(microsoft, days=30)
        self.client.login(username='market-user', password='test-pass-123')

        response = self.client.get(reverse('market_data:stock_chart'), {'stock': microsoft.pk})

        self.assertContains(response, 'name="stock"')
        self.assertContains(response, f'value="{apple.pk}"')
        self.assertContains(response, f'value="{microsoft.pk}" selected')
        self.assertContains(response, reverse('market_data:stock_chart'))

    def test_chart_uses_real_provider_rows_over_sample_rows(self):
        stock = Stock.objects.create(symbol='^GSPC', name='S&P 500')
        sample_time = timezone.datetime(2026, 5, 8, tzinfo=datetime_timezone.utc)
        live_time = timezone.datetime(2026, 5, 8, 13, 30, tzinfo=datetime_timezone.utc)
        PriceData.objects.create(
            stock=stock,
            timestamp=sample_time,
            open_price='185.0000',
            high_price='186.0000',
            low_price='184.0000',
            close_price='185.0000',
            volume=1000,
            source='sample',
        )
        PriceData.objects.create(
            stock=stock,
            timestamp=live_time,
            open_price='7370.0000',
            high_price='7380.0000',
            low_price='7360.0000',
            close_price='7374.5600',
            volume=1000000,
            source='yfinance',
        )

        chart = chart_context(stock, timeframe='1D')

        self.assertEqual([row['source'] for row in chart['payload']['rows']], ['yfinance'])
        self.assertEqual(chart['last_price'], 7374.56)

    def test_chart_payload_includes_rsi_and_excludes_removed_technical_indicators(self):
        stock = Stock.objects.create(symbol='AAPL', name='Apple Inc.')
        seed_sample_prices(stock, days=30)

        chart = chart_context(stock)
        row = chart['payload']['rows'][-1]

        self.assertIn('ema', row)
        self.assertIn('rsi', row)
        self.assertGreaterEqual(row['rsi'], 0)
        self.assertLessEqual(row['rsi'], 100)
        self.assertNotIn('sma', row)
        self.assertNotIn('macd', row)
        self.assertNotIn('macdSignal', row)
        self.assertNotIn('macdHistogram', row)
        self.assertNotIn('bollingerUpper', row)
        self.assertNotIn('bollingerMiddle', row)
        self.assertNotIn('bollingerLower', row)
        self.assertEqual(chart['payload']['indicators'], {'emaPeriod': 50, 'rsiPeriod': 14, 'momentumPeriod': 10})
