"""Market data import and sample-data services.

This module owns all writes to ``PriceData`` that come from external market
providers or from deterministic local sample generation. Views call these
functions and handle user messages; the services raise exceptions when provider
data is missing or malformed so callers can decide how to report failures.
"""

import math
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import PriceData, Stock


COMMODITY_DEFINITIONS = {
    'WTI': {
        'name': 'Crude Oil WTI',
        'exchange': 'Commodity',
        'function': 'WTI',
        'interval': 'daily',
    },
    'GOLD': {
        'name': 'Gold Spot Price',
        'exchange': 'Commodity',
        'function': 'GOLD_SILVER_HISTORY',
        'symbol': 'GOLD',
        'interval': 'daily',
    },
    'NATURAL_GAS': {
        'name': 'Natural Gas',
        'exchange': 'Commodity',
        'function': 'NATURAL_GAS',
        'interval': 'daily',
    },
}

ALPHA_VANTAGE_DAILY_TTL = 15 * 60
ALPHA_VANTAGE_COMMODITY_TTL = 6 * 60 * 60


def to_decimal(value):
    """Convert provider numeric values to the app's four-decimal price scale."""
    return Decimal(str(value)).quantize(Decimal('0.0001'))


def alpha_vantage_daily_cache_key(symbol, outputsize):
    """Build the cache key for Alpha Vantage daily equity responses."""
    return f'av_daily:{symbol.upper()}:{outputsize}'


def alpha_vantage_commodity_cache_key(definition):
    """Build the cache key for an Alpha Vantage commodity definition."""
    symbol = definition.get('symbol') or definition['function']
    return f'av_commodity:{definition["function"]}:{symbol.upper()}'


def commodity_row_value(row):
    """Return the first usable price value from a commodity provider row.

    Alpha Vantage commodity endpoints vary their value key by function, so the
    importer checks the known key names and ignores placeholder values.
    """
    for key in ('value', 'price', 'close', '1. open', '4. close'):
        value = row.get(key)
        if value not in (None, '.', ''):
            return value
    return None


def latest_price(stock):
    """Return the latest close price for ``stock`` or zero when no rows exist."""
    point = stock.price_data.order_by('-timestamp').first()
    return point.close_price if point else Decimal('0')


def safe_cache_get(key):
    """Read from Django's cache while tolerating unavailable cache backends."""
    try:
        return cache.get(key)
    except Exception:
        return None


def safe_cache_set(key, value, timeout):
    """Write to Django's cache without letting cache failures block imports."""
    try:
        cache.set(key, value, timeout)
    except Exception:
        pass


class AlphaVantageClient:
    """Small wrapper around Alpha Vantage HTTP endpoints used by the app.

    The client performs direct HTTPS requests with ``requests`` and caches
    successful JSON payloads to protect both the external API quota and page
    response times during repeated refreshes.
    """

    base_url = 'https://www.alphavantage.co/query'

    def __init__(self, api_key=None):
        """Use the supplied API key or fall back to settings."""
        self.api_key = api_key or settings.ALPHA_VANTAGE_API_KEY

    def daily(self, symbol, outputsize='compact'):
        """Return Alpha Vantage daily OHLCV rows for a stock symbol.

        Raises:
            ValueError: if the API key is missing or Alpha Vantage responds
                without a daily time-series payload.
            requests.HTTPError: if the HTTP response is unsuccessful.
        """
        if not self.api_key:
            raise ValueError('ALPHA_VANTAGE_API_KEY is not configured.')
        cache_key = alpha_vantage_daily_cache_key(symbol, outputsize)
        cached_series = safe_cache_get(cache_key)
        if cached_series is not None:
            return cached_series

        response = requests.get(
            self.base_url,
            params={
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol.upper(),
                'outputsize': outputsize,
                'apikey': self.api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        series = payload.get('Time Series (Daily)')
        if not series:
            message = payload.get('Note') or payload.get('Error Message') or 'No daily time series returned.'
            raise ValueError(message)
        safe_cache_set(cache_key, series, ALPHA_VANTAGE_DAILY_TTL)
        return series

    def commodity_history(self, definition):
        """Return Alpha Vantage commodity history rows for a configured market.

        ``definition`` comes from ``COMMODITY_DEFINITIONS`` and controls the API
        function, optional symbol, and interval. The method raises ``ValueError``
        when the provider returns only an informational or error payload.
        """
        if not self.api_key:
            raise ValueError('ALPHA_VANTAGE_API_KEY is not configured.')
        cache_key = alpha_vantage_commodity_cache_key(definition)
        cached_data = safe_cache_get(cache_key)
        if cached_data is not None:
            return cached_data

        params = {
            'function': definition['function'],
            'interval': definition.get('interval', 'daily'),
            'apikey': self.api_key,
        }
        if definition.get('symbol'):
            params['symbol'] = definition['symbol']
        response = requests.get(self.base_url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        data = payload.get('data')
        if not data:
            message = payload.get('Note') or payload.get('Information') or payload.get('Error Message') or 'No commodity data returned.'
            raise ValueError(message)
        safe_cache_set(cache_key, data, ALPHA_VANTAGE_COMMODITY_TTL)
        return data


def import_alpha_vantage_daily(stock, outputsize='compact'):
    """Import Alpha Vantage daily equity data for a stock.

    Parameters:
        stock: ``Stock`` instance whose symbol will be requested.
        outputsize: Alpha Vantage output size, usually ``compact`` or ``full``.

    Returns:
        The number of newly created ``PriceData`` rows. Existing timestamps are
        updated in place so refreshes stay idempotent.
    """
    series = AlphaVantageClient().daily(stock.symbol, outputsize=outputsize)
    imported = 0
    for day_text, row in series.items():
        day = datetime.combine(date.fromisoformat(day_text), time.min)
        timestamp = timezone.make_aware(day, timezone.get_current_timezone())
        _, created = PriceData.objects.update_or_create(
            stock=stock,
            timestamp=timestamp,
            defaults={
                'open_price': to_decimal(row['1. open']),
                'high_price': to_decimal(row['2. high']),
                'low_price': to_decimal(row['3. low']),
                'close_price': to_decimal(row['4. close']),
                'volume': int(row['5. volume']),
                'source': 'alpha_vantage',
            },
        )
        imported += int(created)
    return imported


def import_alpha_vantage_commodity(symbol):
    """Import a supported Alpha Vantage commodity.

    Parameters:
        symbol: One of the keys in ``COMMODITY_DEFINITIONS``.

    Returns:
        ``(stock, imported_count)`` where ``stock`` is the commodity-backed
        ``Stock`` row and ``imported_count`` is the number of new price rows.

    Raises:
        ValueError: if the symbol is not configured or the provider returns no
        usable data.
    """
    key = symbol.upper().strip()
    if key not in COMMODITY_DEFINITIONS:
        raise ValueError(f'Unsupported commodity: {symbol}')

    definition = COMMODITY_DEFINITIONS[key]
    stock, _ = Stock.objects.get_or_create(
        symbol=key,
        defaults={
            'name': definition['name'],
            'exchange': definition['exchange'],
            'currency': 'USD',
        },
    )
    data = AlphaVantageClient().commodity_history(definition)
    imported = 0

    for row in data:
        # Commodity rows usually carry one price value, so OHLC are all set to
        # that value to keep charting and backtesting code using the same model.
        value = commodity_row_value(row)
        if value is None:
            continue
        day = datetime.combine(date.fromisoformat(row['date']), time.min)
        timestamp = timezone.make_aware(day, timezone.get_current_timezone())
        price = to_decimal(value)
        _, created = PriceData.objects.update_or_create(
            stock=stock,
            timestamp=timestamp,
            defaults={
                'open_price': price,
                'high_price': price,
                'low_price': price,
                'close_price': price,
                'volume': 0,
                'source': f'alpha_vantage_{definition["function"].lower()}',
            },
        )
        imported += int(created)
    return stock, imported


def import_default_commodities():
    """Import the default commodity set shown from the market-data screen."""
    results = []
    for symbol in ('WTI', 'GOLD', 'NATURAL_GAS'):
        results.append(import_alpha_vantage_commodity(symbol))
    return results


def seed_sample_prices(stock, days=260):
    """Create deterministic OHLCV data so the simulator works without API access.

    Parameters:
        stock: ``Stock`` receiving generated business-day price rows.
        days: Number of trading days to create.

    Returns:
        Number of new rows inserted. Re-running for the same stock and dates is
        safe because rows are matched by the stock/timestamp unique constraint.
    """
    rng = random.Random(stock.symbol)
    start = timezone.now().date() - timedelta(days=days + 40)
    price = Decimal('80.0000') + Decimal(rng.randint(0, 9000)) / Decimal('100')
    created = 0
    day_index = 0

    for offset in range(days + 40):
        current_day = start + timedelta(days=offset)
        if current_day.weekday() >= 5:
            continue
        # The wave/drift/noise blend produces varied but repeatable prices for
        # demos, tests, and local development without external API access.
        wave = Decimal(str(math.sin(day_index / 13) * 1.2)).quantize(Decimal('0.0001'))
        drift = Decimal('0.0350')
        noise = Decimal(str(rng.uniform(-1.4, 1.4))).quantize(Decimal('0.0001'))
        open_price = max(Decimal('1'), price + noise)
        close_price = max(Decimal('1'), open_price + drift + wave + Decimal(str(rng.uniform(-0.9, 0.9))))
        high_price = max(open_price, close_price) + Decimal(str(rng.uniform(0.2, 2.2)))
        low_price = max(Decimal('0.5'), min(open_price, close_price) - Decimal(str(rng.uniform(0.2, 2.0))))
        volume = rng.randint(900_000, 8_000_000)
        timestamp = timezone.make_aware(datetime.combine(current_day, time.min))

        _, was_created = PriceData.objects.update_or_create(
            stock=stock,
            timestamp=timestamp,
            defaults={
                'open_price': to_decimal(open_price),
                'high_price': to_decimal(high_price),
                'low_price': to_decimal(low_price),
                'close_price': to_decimal(close_price),
                'volume': volume,
                'source': 'sample',
            },
        )
        created += int(was_created)
        price = close_price
        day_index += 1
        if day_index >= days:
            break
    return created
