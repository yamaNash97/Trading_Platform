from decimal import Decimal


def sma(values, window):
    output = []
    running = Decimal('0')
    for index, value in enumerate(values):
        running += value
        if index >= window:
            running -= values[index - window]
        output.append(running / Decimal(window) if index >= window - 1 else None)
    return output


def rsi(values, period):
    output = [None] * len(values)
    if len(values) <= period:
        return output

    gains = []
    losses = []
    for index in range(1, period + 1):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, Decimal('0')))
        losses.append(abs(min(delta, Decimal('0'))))

    avg_gain = sum(gains, Decimal('0')) / Decimal(period)
    avg_loss = sum(losses, Decimal('0')) / Decimal(period)
    output[period] = Decimal('100') if avg_loss == 0 else Decimal('100') - (Decimal('100') / (Decimal('1') + avg_gain / avg_loss))

    for index in range(period + 1, len(values)):
        delta = values[index] - values[index - 1]
        gain = max(delta, Decimal('0'))
        loss = abs(min(delta, Decimal('0')))
        avg_gain = ((avg_gain * Decimal(period - 1)) + gain) / Decimal(period)
        avg_loss = ((avg_loss * Decimal(period - 1)) + loss) / Decimal(period)
        output[index] = Decimal('100') if avg_loss == 0 else Decimal('100') - (Decimal('100') / (Decimal('1') + avg_gain / avg_loss))
    return output


def generate_signals(strategy, prices):
    closes = [point.close_price for point in prices]
    short_ma = sma(closes, strategy.short_window)
    long_ma = sma(closes, strategy.long_window)
    rsi_values = rsi(closes, strategy.rsi_period)
    signals = []

    for index, point in enumerate(prices):
        signal = 'hold'
        previous_short = short_ma[index - 1] if index else None
        previous_long = long_ma[index - 1] if index else None
        crossed_up = (
            previous_short is not None
            and previous_long is not None
            and short_ma[index] is not None
            and long_ma[index] is not None
            and previous_short <= previous_long
            and short_ma[index] > long_ma[index]
        )
        crossed_down = (
            previous_short is not None
            and previous_long is not None
            and short_ma[index] is not None
            and long_ma[index] is not None
            and previous_short >= previous_long
            and short_ma[index] < long_ma[index]
        )
        rsi_buy = rsi_values[index] is not None and rsi_values[index] <= Decimal(strategy.rsi_buy_threshold)
        rsi_sell = rsi_values[index] is not None and rsi_values[index] >= Decimal(strategy.rsi_sell_threshold)

        if strategy.strategy_type == strategy.StrategyType.MOVING_AVERAGE:
            signal = 'buy' if crossed_up else 'sell' if crossed_down else 'hold'
        elif strategy.strategy_type == strategy.StrategyType.RSI:
            signal = 'buy' if rsi_buy else 'sell' if rsi_sell else 'hold'
        elif strategy.strategy_type == strategy.StrategyType.COMBINED:
            signal = 'buy' if crossed_up and not rsi_sell else 'sell' if crossed_down or rsi_sell else 'hold'

        signals.append(
            {
                'price': point,
                'signal': signal,
                'short_ma': short_ma[index],
                'long_ma': long_ma[index],
                'rsi': rsi_values[index],
            }
        )
    return signals
