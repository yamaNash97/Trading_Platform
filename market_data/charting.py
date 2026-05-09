import math
from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import PriceData, Stock
from .services import to_decimal


def finite_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def refresh_yfinance_prices(stock, period='5d', interval='15m'):
    try:
        import yfinance as yf
    except ModuleNotFoundError as exc:
        raise RuntimeError('yfinance is not installed. Run pip install -r requirements.txt to enable live prices.') from exc

    history = yf.Ticker(stock.symbol).history(
        period=period,
        interval=interval,
        auto_adjust=False,
        actions=False,
        timeout=8,
        raise_errors=False,
    )
    if history is None or history.empty:
        raise RuntimeError(f'No live yfinance prices were returned for {stock.symbol}. Showing saved prices instead.')

    imported = 0
    current_tz = timezone.get_current_timezone()
    for row_index, row in history.tail(180).iterrows():
        close = finite_float(row.get('Close'))
        if close is None:
            continue
        opened = finite_float(row.get('Open')) or close
        high = finite_float(row.get('High')) or max(opened, close)
        low = finite_float(row.get('Low')) or min(opened, close)
        volume = finite_float(row.get('Volume')) or 0
        timestamp = row_index.to_pydatetime() if hasattr(row_index, 'to_pydatetime') else row_index
        if not isinstance(timestamp, datetime):
            timestamp = datetime.combine(timestamp, time.min)
        if timezone.is_naive(timestamp):
            timestamp = timezone.make_aware(timestamp, current_tz)
        else:
            timestamp = timestamp.astimezone(current_tz)

        _, created = PriceData.objects.update_or_create(
            stock=stock,
            timestamp=timestamp,
            defaults={
                'open_price': to_decimal(opened),
                'high_price': to_decimal(high),
                'low_price': to_decimal(low),
                'close_price': to_decimal(close),
                'volume': int(volume),
                'source': 'yfinance',
            },
        )
        imported += int(created)
    return imported


def with_indicators(prices, rsi_period=14, ema_period=50):
    alpha = 2 / (ema_period + 1)
    ema = None
    avg_gain = None
    avg_loss = None
    gains = []
    losses = []
    previous = None
    rows = []

    for index, price in enumerate(prices):
        close = float(price.close_price)
        ema = close if ema is None else (close * alpha) + (ema * (1 - alpha))

        rsi = None
        if previous is not None:
            change = close - previous
            gain = max(change, 0)
            loss = max(-change, 0)
            if len(gains) < rsi_period:
                gains.append(gain)
                losses.append(loss)
                if len(gains) == rsi_period:
                    avg_gain = sum(gains) / rsi_period
                    avg_loss = sum(losses) / rsi_period
            else:
                avg_gain = ((avg_gain * (rsi_period - 1)) + gain) / rsi_period
                avg_loss = ((avg_loss * (rsi_period - 1)) + loss) / rsi_period

            if avg_gain is not None and avg_loss is not None:
                rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss)))

        rows.append(
            {
                'timestamp': price.timestamp,
                'close': close,
                'ema': ema,
                'rsi': rsi,
                'source': price.source,
                'is_live': price.source == 'yfinance',
                'index': index,
            }
        )
        previous = close
    return rows


def svg_path(rows, value_key, minimum, maximum, top, height, left=55, width=900):
    points = []
    usable_range = maximum - minimum
    for row in rows:
        value = row.get(value_key)
        if value is None:
            continue
        x = left + ((row['index'] / max(len(rows) - 1, 1)) * width)
        y = top + ((maximum - value) / usable_range * height)
        points.append(f'{x:.1f},{y:.1f}')
    return ' '.join(points)


def chart_context(stock, start_date=None, end_date=None, refresh_live=False, limit=120):
    warning = ''
    if refresh_live:
        try:
            refresh_yfinance_prices(stock)
        except RuntimeError as exc:
            warning = str(exc)
        except Exception as exc:
            warning = f'Live price refresh failed: {exc}'

    prices = PriceData.objects.filter(stock=stock).order_by('timestamp')
    if start_date:
        prices = prices.filter(timestamp__date__gte=start_date)
    if end_date:
        prices = prices.filter(timestamp__date__lte=end_date)
    prices = list(prices)
    if len(prices) > limit:
        prices = prices[-limit:]

    rows = with_indicators(prices)
    if len(rows) < 2:
        return {
            'stock': stock,
            'has_data': False,
            'warning': warning,
        }

    values = [row['close'] for row in rows] + [row['ema'] for row in rows if row['ema'] is not None]
    minimum = min(values)
    maximum = max(values)
    padding = max((maximum - minimum) * 0.08, 1)
    minimum -= padding
    maximum += padding

    first = rows[0]
    latest = rows[-1]
    change = latest['close'] - first['close']
    change_percent = (change / first['close'] * 100) if first['close'] else 0
    midpoint = minimum + ((maximum - minimum) / 2)
    price_grid = [
        {'label': f'{maximum:.2f}', 'y': 70},
        {'label': f'{midpoint:.2f}', 'y': 175},
        {'label': f'{minimum:.2f}', 'y': 280},
    ]

    return {
        'stock': stock,
        'has_data': True,
        'warning': warning,
        'last_price': latest['close'],
        'change': change,
        'change_percent': change_percent,
        'latest_time': latest['timestamp'],
        'first_time': first['timestamp'],
        'price_path': svg_path(rows, 'close', minimum, maximum, 70, 210),
        'ema_path': svg_path(rows, 'ema', minimum, maximum, 70, 210),
        'rsi_path': svg_path(rows, 'rsi', 0, 100, 315, 70),
        'rsi_70_y': 315 + ((100 - 70) / 100 * 70),
        'rsi_30_y': 315 + ((100 - 30) / 100 * 70),
        'price_grid': price_grid,
        'is_positive': change >= 0,
        'is_live': latest['is_live'],
        'source_label': 'Live via yfinance' if latest['is_live'] else 'Saved market data',
        'next_refresh': timezone.now() + timedelta(seconds=45),
    }


def chart_context_for_first_stock(refresh_live=False):
    stock = Stock.objects.order_by('symbol').first()
    if not stock:
        return {'stock': None, 'has_data': False, 'warning': 'Add a stock to load a chart.'}
    return chart_context(stock, refresh_live=refresh_live)
