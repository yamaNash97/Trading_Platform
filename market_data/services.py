import math
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import requests
from django.conf import settings
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


def to_decimal(value):
    return Decimal(str(value)).quantize(Decimal('0.0001'))


def commodity_row_value(row):
    for key in ('value', 'price', 'close', '1. open', '4. close'):
        value = row.get(key)
        if value not in (None, '.', ''):
            return value
    return None


def latest_price(stock):
    point = stock.price_data.order_by('-timestamp').first()
    return point.close_price if point else Decimal('0')


class AlphaVantageClient:
    base_url = 'https://www.alphavantage.co/query'

    def __init__(self, api_key=None):
        self.api_key = api_key or settings.ALPHA_VANTAGE_API_KEY

    def daily(self, symbol, outputsize='compact'):
        if not self.api_key:
            raise ValueError('ALPHA_VANTAGE_API_KEY is not configured.')
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
        return series

    def commodity_history(self, definition):
        if not self.api_key:
            raise ValueError('ALPHA_VANTAGE_API_KEY is not configured.')
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
        return data


def import_alpha_vantage_daily(stock, outputsize='compact'):
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
    results = []
    for symbol in ('WTI', 'GOLD', 'NATURAL_GAS'):
        results.append(import_alpha_vantage_commodity(symbol))
    return results


def seed_sample_prices(stock, days=260):
    """Create deterministic OHLCV data so the simulator works without API access."""
    rng = random.Random(stock.symbol)
    start = timezone.now().date() - timedelta(days=days + 40)
    price = Decimal('80.0000') + Decimal(rng.randint(0, 9000)) / Decimal('100')
    created = 0
    day_index = 0

    for offset in range(days + 40):
        current_day = start + timedelta(days=offset)
        if current_day.weekday() >= 5:
            continue
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
