"""Market data import and sample price services.

This module writes ``PriceData`` rows from market data APIs or from local sample
data. Views call these functions and show user messages. The functions raise
errors when API data is missing or invalid.
"""

import math
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
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

COMMODITY_SYMBOL_ALIASES = {
    'CL=F': 'WTI',
    'GC=F': 'GOLD',
    'GOLD': 'GOLD',
    'NG=F': 'NATURAL_GAS',
    'NATGAS': 'NATURAL_GAS',
    'NATURAL_GAS': 'NATURAL_GAS',
    'WTI': 'WTI',
    'XAU': 'GOLD',
}

ALPHA_VANTAGE_DAILY_TTL = 15 * 60
ALPHA_VANTAGE_COMMODITY_TTL = 6 * 60 * 60
PRICE_DATA_UPDATE_FIELDS = [
    'open_price',
    'high_price',
    'low_price',
    'close_price',
    'volume',
    'source',
]


def to_decimal(value):
    """Convert API numbers to the app's four-decimal price scale."""
    return Decimal(str(value)).quantize(Decimal('0.0001'))


def alpha_vantage_daily_cache_key(symbol):
    """Build the cache key for Alpha Vantage daily stock data."""
    return f'av_daily:{symbol.upper()}:compact'


def alpha_vantage_commodity_cache_key(definition):
    """Build the cache key for Alpha Vantage commodity data."""
    symbol = definition.get('symbol') or definition['function']
    return f'av_commodity:{definition["function"]}:{symbol.upper()}'


def commodity_row_value(row):
    """Return the first usable price from a commodity API row.

    Alpha Vantage uses different field names for different commodities, so this
    helper checks the known names and skips blank values.
    """
    for key in ('value', 'price', 'close', '1. open', '4. close'):
        value = row.get(key)
        if value not in (None, '.', ''):
            return value
    return None


def alpha_vantage_commodity_key(symbol):
    """Return the supported commodity key for a user-entered symbol."""
    cleaned = symbol.upper().strip()
    return COMMODITY_SYMBOL_ALIASES.get(cleaned, cleaned)


def is_alpha_vantage_commodity_symbol(symbol):
    """Return true when ``symbol`` can use a free Alpha Vantage commodity feed."""
    return alpha_vantage_commodity_key(symbol) in COMMODITY_DEFINITIONS


def price_row_changed(existing, incoming):
    """Return true when a saved price row differs from incoming API data."""
    return any(getattr(existing, field) != getattr(incoming, field) for field in PRICE_DATA_UPDATE_FIELDS)


def sync_price_rows(stock, rows):
    """Bulk create new price rows and update changed existing rows.

    The API endpoints often return full history. Avoiding writes for unchanged
    rows keeps repeated imports fast and reduces SQLite lock contention.
    """
    incoming_by_timestamp = {row.timestamp: row for row in rows}
    if not incoming_by_timestamp:
        return 0

    existing_by_timestamp = {
        row.timestamp: row
        for row in PriceData.objects.filter(stock=stock, timestamp__in=incoming_by_timestamp.keys()).only(
            'id',
            'timestamp',
            *PRICE_DATA_UPDATE_FIELDS,
        )
    }
    rows_to_create = []
    rows_to_update = []

    for timestamp, incoming in incoming_by_timestamp.items():
        existing = existing_by_timestamp.get(timestamp)
        if existing is None:
            rows_to_create.append(incoming)
        elif price_row_changed(existing, incoming):
            for field in PRICE_DATA_UPDATE_FIELDS:
                setattr(existing, field, getattr(incoming, field))
            rows_to_update.append(existing)

    with transaction.atomic():
        if rows_to_create:
            PriceData.objects.bulk_create(
                rows_to_create,
                batch_size=200,
                update_conflicts=True,
                unique_fields=['stock', 'timestamp'],
                update_fields=PRICE_DATA_UPDATE_FIELDS,
            )
        if rows_to_update:
            PriceData.objects.bulk_update(rows_to_update, PRICE_DATA_UPDATE_FIELDS, batch_size=200)

    return len(rows_to_create)


def latest_price(stock):
    """Return the latest preferred close price for ``stock`` or zero.

    Live/imported providers are preferred over sample rows so demo data cannot
    mask a fresher real market refresh.
    """
    point = stock.price_data.exclude(source='sample').order_by('-timestamp').first()
    if point is None:
        point = stock.price_data.order_by('-timestamp').first()
    return point.close_price if point else Decimal('0')


def safe_cache_get(key):
    """Read from Django's cache and ignore cache errors."""
    try:
        return cache.get(key)
    except Exception:
        return None


def safe_cache_set(key, value, timeout):
    """Write to Django's cache and ignore cache errors."""
    try:
        cache.set(key, value, timeout)
    except Exception:
        pass


class AlphaVantageClient:
    """Small wrapper around the Alpha Vantage API used by the app.

    The client uses ``requests`` and caches good JSON results. That helps avoid
    extra API calls and keeps repeated refreshes faster.
    """

    base_url = 'https://www.alphavantage.co/query'

    def __init__(self, api_key=None):
        """Use the given API key or the key from settings."""
        self.api_key = api_key or settings.ALPHA_VANTAGE_API_KEY

    def daily(self, symbol):
        """Return free Alpha Vantage daily OHLCV rows for a stock symbol.

        Raises:
            ValueError: if the API key is missing or Alpha Vantage responds
                without daily prices.
            requests.HTTPError: if the HTTP request fails.
        """
        if not self.api_key:
            raise ValueError('ALPHA_VANTAGE_API_KEY is not configured.')
        cache_key = alpha_vantage_daily_cache_key(symbol)
        cached_series = safe_cache_get(cache_key)
        if cached_series is not None:
            return cached_series

        response = requests.get(
            self.base_url,
            params={
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol.upper(),
                'outputsize': 'compact',
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
        """Return Alpha Vantage commodity history rows.

        ``definition`` comes from ``COMMODITY_DEFINITIONS`` and sets the API
        function, optional symbol, and interval. The method raises ``ValueError``
        when Alpha Vantage returns only an info or error message.
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


def import_alpha_vantage_daily(stock):
    """Import free Alpha Vantage daily equity data for a stock.

    Parameters:
        stock: ``Stock`` instance whose symbol will be requested.

    Returns:
        The number of new ``PriceData`` rows. Existing timestamps are updated,
        so running the import again is safe.
    """
    series = AlphaVantageClient().daily(stock.symbol)
    rows = []
    for day_text, row in series.items():
        day = datetime.combine(date.fromisoformat(day_text), time.min)
        timestamp = timezone.make_aware(day, timezone.get_current_timezone())
        rows.append(
            PriceData(
                stock=stock,
                timestamp=timestamp,
                open_price=to_decimal(row['1. open']),
                high_price=to_decimal(row['2. high']),
                low_price=to_decimal(row['3. low']),
                close_price=to_decimal(row['4. close']),
                volume=int(row['5. volume']),
                source='alpha_vantage',
            )
        )
    return sync_price_rows(stock, rows)


def import_alpha_vantage_commodity(symbol, stock=None):
    """Import a supported Alpha Vantage commodity.

    Parameters:
        symbol: One of the keys in ``COMMODITY_DEFINITIONS`` or a supported
            alias like ``GC=F``.
        stock: Optional existing ``Stock`` row to receive imported prices.

    Returns:
        ``(stock, imported_count)`` where ``stock`` is the commodity ``Stock``
        row and ``imported_count`` is the number of new price rows.

    Raises:
        ValueError: if the symbol is not supported or the API returns no
        usable data.
    """
    key = alpha_vantage_commodity_key(symbol)
    if key not in COMMODITY_DEFINITIONS:
        raise ValueError(f'Unsupported commodity: {symbol}')

    definition = COMMODITY_DEFINITIONS[key]
    if stock is None:
        stock, _ = Stock.objects.get_or_create(
            symbol=key,
            defaults={
                'name': definition['name'],
                'exchange': definition['exchange'],
                'currency': 'USD',
            },
        )
    data = AlphaVantageClient().commodity_history(definition)
    rows = []

    for row in data:
        # Commodity rows usually have one price value, so OHLC all use that
        # value and the rest of the app can use the same model.
        value = commodity_row_value(row)
        if value is None:
            continue
        day = datetime.combine(date.fromisoformat(row['date']), time.min)
        timestamp = timezone.make_aware(day, timezone.get_current_timezone())
        price = to_decimal(value)
        rows.append(
            PriceData(
                stock=stock,
                timestamp=timestamp,
                open_price=price,
                high_price=price,
                low_price=price,
                close_price=price,
                volume=0,
                source=f'alpha_vantage_{definition["function"].lower()}',
            )
        )
    return stock, sync_price_rows(stock, rows)


def import_default_commodities():
    """Import the default commodities shown on the market-data screen."""
    results = []
    for symbol in ('WTI', 'GOLD', 'NATURAL_GAS'):
        results.append(import_alpha_vantage_commodity(symbol))
    return results


def seed_sample_prices(stock, days=260):
    """Create repeatable OHLCV data so the app works without API access.

    Parameters:
        stock: ``Stock`` that receives sample weekday price rows.
        days: Number of trading days to create.

    Returns:
        Number of new rows added. Running it again for the same stock and dates
        is safe because each stock/timestamp pair is unique.
    """
    if days <= 0:
        return 0

    rng = random.Random(stock.symbol)
    calendar_span = math.ceil(days * 7 / 5) + 10
    start = timezone.now().date() - timedelta(days=calendar_span)
    price = Decimal('80.0000') + Decimal(rng.randint(0, 9000)) / Decimal('100')
    day_index = 0
    rows = []

    for offset in range(calendar_span + 1):
        current_day = start + timedelta(days=offset)
        if current_day.weekday() >= 5:
            continue
        # This small mix of wave, drift, and noise makes prices varied but
        # repeatable for demos, tests, and local work.
        wave = Decimal(str(math.sin(day_index / 13) * 1.2)).quantize(Decimal('0.0001'))
        drift = Decimal('0.0350')
        noise = Decimal(str(rng.uniform(-1.4, 1.4))).quantize(Decimal('0.0001'))
        open_price = max(Decimal('1'), price + noise)
        close_price = max(Decimal('1'), open_price + drift + wave + Decimal(str(rng.uniform(-0.9, 0.9))))
        high_price = max(open_price, close_price) + Decimal(str(rng.uniform(0.2, 2.2)))
        low_price = max(Decimal('0.5'), min(open_price, close_price) - Decimal(str(rng.uniform(0.2, 2.0))))
        volume = rng.randint(900_000, 8_000_000)
        timestamp = timezone.make_aware(datetime.combine(current_day, time.min))

        rows.append(
            PriceData(
                stock=stock,
                timestamp=timestamp,
                open_price=to_decimal(open_price),
                high_price=to_decimal(high_price),
                low_price=to_decimal(low_price),
                close_price=to_decimal(close_price),
                volume=volume,
                source='sample',
            )
        )
        price = close_price
        day_index += 1
        if day_index >= days:
            break

    if not rows:
        return 0

    timestamps = [row.timestamp for row in rows]
    existing_timestamps = set(
        PriceData.objects.filter(stock=stock, timestamp__in=timestamps).values_list('timestamp', flat=True)
    )
    created = sum(1 for row in rows if row.timestamp not in existing_timestamps)

    with transaction.atomic():
        PriceData.objects.bulk_create(
            rows,
            batch_size=200,
            update_conflicts=True,
            unique_fields=['stock', 'timestamp'],
            update_fields=[
                'open_price',
                'high_price',
                'low_price',
                'close_price',
                'volume',
                'source',
            ],
        )

    return created
