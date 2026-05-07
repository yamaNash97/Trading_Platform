import math
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

from .models import PriceData


def to_decimal(value):
    return Decimal(str(value)).quantize(Decimal('0.0001'))


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
