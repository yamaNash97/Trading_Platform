import math
from datetime import datetime, time, timedelta
from statistics import pstdev
from uuid import uuid4

from django.utils import timezone

from .models import PriceData
from .services import to_decimal


DEFAULT_TIMEFRAME = '3M'
TIMEFRAME_OPTIONS = (
    ('1D', '1D', timedelta(days=1)),
    ('1W', '1W', timedelta(days=7)),
    ('1M', '1M', timedelta(days=31)),
    ('3M', '3M', timedelta(days=93)),
    ('1Y', '1Y', timedelta(days=366)),
)
REFRESH_INTERVAL_OPTIONS = (15, 30, 45, 60, 120)


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


def normalise_timeframe(value, default=DEFAULT_TIMEFRAME):
    valid_values = {option[0] for option in TIMEFRAME_OPTIONS}
    value = (value or default or '').upper()
    if value in valid_values:
        return value
    return default if default in valid_values else None


def chart_request_options(request, default_refresh_live=False, default_timeframe=DEFAULT_TIMEFRAME):
    refresh_value = request.GET.get('refresh')
    refresh_live = default_refresh_live if refresh_value is None else refresh_value == '1'
    return {
        'refresh_live': refresh_live,
        'timeframe': normalise_timeframe(request.GET.get('timeframe'), default=default_timeframe),
    }
def source_label(source):
    if source == 'yfinance':
        return 'Live via yfinance'
    if source == 'sample':
        return 'Saved sample data'
    if source == 'alpha_vantage':
        return 'Alpha Vantage'
    if source and source.startswith('alpha_vantage_'):
        return 'Alpha Vantage commodity'
    return 'Saved market data'


def exponential_moving_average(values, period):
    alpha = 2 / (period + 1)
    ema = None
    averages = []
    for value in values:
        ema = value if ema is None else (value * alpha) + (ema * (1 - alpha))
        averages.append(ema)
    return averages


def simple_moving_average(values, period):
    averages = []
    window = []
    running_total = 0
    for value in values:
        window.append(value)
        running_total += value
        if len(window) > period:
            running_total -= window.pop(0)
        averages.append(running_total / period if len(window) == period else None)
    return averages


def relative_strength_index(values, period=14):
    if not values:
        return []

    rsi_values = [None]
    gains = []
    losses = []
    avg_gain = None
    avg_loss = None

    for index in range(1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0)
        loss = max(-change, 0)

        if len(gains) < period:
            gains.append(gain)
            losses.append(loss)
            if len(gains) == period:
                avg_gain = sum(gains) / period
                avg_loss = sum(losses) / period
        else:
            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period

        if avg_gain is None or avg_loss is None:
            rsi_values.append(None)
        else:
            rsi_values.append(100 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss))))

    return rsi_values


def moving_average_convergence_divergence(values, fast_period=12, slow_period=26, signal_period=9):
    fast = exponential_moving_average(values, fast_period)
    slow = exponential_moving_average(values, slow_period)
    macd = [fast_value - slow_value for fast_value, slow_value in zip(fast, slow)]
    signal = exponential_moving_average(macd, signal_period)
    histogram = [macd_value - signal_value for macd_value, signal_value in zip(macd, signal)]
    return macd, signal, histogram


def bollinger_bands(values, period=20, deviations=2):
    middle = simple_moving_average(values, period)
    upper = []
    lower = []
    for index, average in enumerate(middle):
        if average is None:
            upper.append(None)
            lower.append(None)
            continue
        window = values[index - period + 1:index + 1]
        band_width = pstdev(window) * deviations
        upper.append(average + band_width)
        lower.append(average - band_width)
    return upper, middle, lower


def with_indicators(prices, rsi_period=14, ema_period=50, sma_period=20, momentum_period=10):
    closes = [float(price.close_price) for price in prices]
    ema_values = exponential_moving_average(closes, ema_period)
    sma_values = simple_moving_average(closes, sma_period)
    rsi_values = relative_strength_index(closes, rsi_period)
    macd_values, macd_signal_values, macd_histogram_values = moving_average_convergence_divergence(closes)
    bollinger_upper_values, bollinger_middle_values, bollinger_lower_values = bollinger_bands(closes, sma_period)
    first_close = closes[0] if closes else None
    rows = []

    for index, price in enumerate(prices):
        close = closes[index]
        previous_close = closes[index - 1] if index else None
        momentum = close - closes[index - momentum_period] if index >= momentum_period else None
        velocity = ((close - previous_close) / previous_close * 100) if previous_close else None
        change_percent = ((close - first_close) / first_close * 100) if first_close else 0

        rows.append(
            {
                'timestamp': timezone.localtime(price.timestamp),
                'open': float(price.open_price),
                'high': float(price.high_price),
                'low': float(price.low_price),
                'close': close,
                'volume': int(price.volume),
                'ema': ema_values[index],
                'sma': sma_values[index],
                'rsi': rsi_values[index],
                'macd': macd_values[index],
                'macd_signal': macd_signal_values[index],
                'macd_histogram': macd_histogram_values[index],
                'bollinger_upper': bollinger_upper_values[index],
                'bollinger_middle': bollinger_middle_values[index],
                'bollinger_lower': bollinger_lower_values[index],
                'momentum': momentum,
                'velocity': velocity,
                'change_percent': change_percent,
                'source': price.source,
                'is_live': price.source == 'yfinance',
                'index': index,
            }
        )
    return rows


def serialise_number(value, digits=4):
    if value is None:
        return None
    return round(float(value), digits)


def serialise_chart_row(row):
    timestamp = row['timestamp']
    return {
        'timestamp': timestamp.isoformat(),
        'timestampLabel': timestamp.strftime('%b %d, %Y %H:%M'),
        'open': serialise_number(row['open']),
        'high': serialise_number(row['high']),
        'low': serialise_number(row['low']),
        'close': serialise_number(row['close']),
        'volume': row['volume'],
        'ema': serialise_number(row['ema']),
        'sma': serialise_number(row['sma']),
        'rsi': serialise_number(row['rsi']),
        'macd': serialise_number(row['macd']),
        'macdSignal': serialise_number(row['macd_signal']),
        'macdHistogram': serialise_number(row['macd_histogram']),
        'bollingerUpper': serialise_number(row['bollinger_upper']),
        'bollingerMiddle': serialise_number(row['bollinger_middle']),
        'bollingerLower': serialise_number(row['bollinger_lower']),
        'momentum': serialise_number(row['momentum']),
        'velocity': serialise_number(row['velocity']),
        'changePercent': serialise_number(row['change_percent']),
        'source': row['source'],
        'isLive': row['is_live'],
    }


def price_axis(rows):
    values = []
    for row in rows:
        values.extend([row['open'], row['high'], row['low'], row['close'], row['ema']])
        for key in ('sma', 'bollinger_upper', 'bollinger_lower'):
            if row.get(key) is not None:
                values.append(row[key])
    minimum = min(values)
    maximum = max(values)
    first_close = rows[0]['close'] if rows else 0
    step = max(abs(first_close) * 0.05, 0.01)
    padding = max((maximum - minimum) * 0.08, step)
    axis_min = math.floor((minimum - padding) / step) * step
    axis_max = math.ceil((maximum + padding) / step) * step
    return {
        'min': serialise_number(axis_min),
        'max': serialise_number(axis_max),
        'step': serialise_number(step),
    }


def chart_context(stock, start_date=None, end_date=None, refresh_live=False, limit=500, timeframe=DEFAULT_TIMEFRAME):
    warning = ''
    if refresh_live:
        try:
            refresh_yfinance_prices(stock)
        except RuntimeError as exc:
            warning = str(exc)
        except Exception as exc:
            warning = f'Live price refresh failed: {exc}'

    active_timeframe = normalise_timeframe(timeframe, default=None)
    prices = PriceData.objects.filter(stock=stock).order_by('timestamp')
    if start_date:
        prices = prices.filter(timestamp__date__gte=start_date)
    if end_date:
        prices = prices.filter(timestamp__date__lte=end_date)

    latest_price = prices.order_by('-timestamp').first()
    if active_timeframe and latest_price:
        timeframe_delta = dict((value, delta) for value, _label, delta in TIMEFRAME_OPTIONS)[active_timeframe]
        prices = prices.filter(timestamp__gte=latest_price.timestamp - timeframe_delta)

    prices = list(prices)
    if len(prices) > limit:
        prices = prices[-limit:]

    rows = with_indicators(prices)
    if not rows:
        chart_id = f'market-chart-{stock.pk}-{uuid4().hex[:8]}' if stock else f'market-chart-empty-{uuid4().hex[:8]}'
        return {
            'stock': stock,
            'has_data': False,
            'warning': warning,
            'dom_id': chart_id,
            'timeframes': [
                {'value': value, 'label': label, 'active': value == active_timeframe}
                for value, label, _delta in TIMEFRAME_OPTIONS
            ],
            'refresh_intervals': REFRESH_INTERVAL_OPTIONS,
            'active_timeframe': active_timeframe,
            'default_refresh_interval': 45,
        }

    first = rows[0]
    latest = rows[-1]
    change = latest['close'] - first['close']
    change_percent = (change / first['close'] * 100) if first['close'] else 0
    chart_id = f'market-chart-{stock.pk}-{uuid4().hex[:8]}'
    latest_source_label = source_label(latest['source'])

    return {
        'stock': stock,
        'has_data': True,
        'warning': warning,
        'last_price': latest['close'],
        'last_open': latest['open'],
        'last_high': latest['high'],
        'last_low': latest['low'],
        'change': change,
        'change_percent': change_percent,
        'latest_time': latest['timestamp'],
        'first_time': first['timestamp'],
        'dom_id': chart_id,
        'json_id': f'{chart_id}-data',
        'active_timeframe': active_timeframe,
        'timeframes': [
            {'value': value, 'label': label, 'active': value == active_timeframe}
            for value, label, _delta in TIMEFRAME_OPTIONS
        ],
        'refresh_intervals': REFRESH_INTERVAL_OPTIONS,
        'default_refresh_interval': 45,
        'is_positive': change >= 0,
        'is_live': latest['is_live'],
        'source_label': latest_source_label,
        'next_refresh': timezone.now() + timedelta(seconds=45),
        'payload': {
            'symbol': stock.symbol,
            'currency': stock.currency,
            'timeframe': active_timeframe,
            'rows': [serialise_chart_row(row) for row in rows],
            'priceAxis': price_axis(rows),
            'sourceLabel': latest_source_label,
            'lastUpdated': latest['timestamp'].isoformat(),
            'lastUpdatedLabel': latest['timestamp'].strftime('%b %d, %Y %H:%M'),
            'change': serialise_number(change),
            'changePercent': serialise_number(change_percent),
            'isPositive': change >= 0,
            'indicators': {
                'emaPeriod': 50,
                'smaPeriod': 20,
                'rsiPeriod': 14,
                'macdFast': 12,
                'macdSlow': 26,
                'macdSignal': 9,
                'bollingerPeriod': 20,
                'bollingerDeviations': 2,
                'momentumPeriod': 10,
            },
        },
    }
