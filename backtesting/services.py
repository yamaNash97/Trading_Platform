"""Backtesting engine and result check helpers.

This module runs strategies over old prices, records simulated trades, and
calculates account numbers such as total return and max drawdown. Views call
these functions and show user messages.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from market_data.models import PriceData
from strategies.services import generate_signals

from .models import BacktestResult, BacktestTrade


def money(value):
    """Round a Decimal-like value to cents."""
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def percent(value):
    """Round a Decimal-like value to a two-decimal percentage."""
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def quantity(value):
    """Round a simulated share quantity to six decimal places."""
    return Decimal(value).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)


def backtest_price_queryset(stock, start_date, end_date):
    """Return the ordered price rows used by the backtest engine."""
    price_query = stock.price_data.filter(
        timestamp__date__gte=start_date,
        timestamp__date__lte=end_date,
    )
    # Prefer imported/live rows over sample rows when both exist, so one
    # backtest does not mix different price sources.
    if price_query.exclude(source='sample').exists():
        price_query = price_query.exclude(source='sample')
    return price_query.order_by('timestamp')


def trade_source_issues(result):
    """Find completed trades whose entry and exit prices came from different sources.

    Returns:
        A list of dictionaries used by the report template to warn about saved
        older results that mixed sample and live/imported price rows.
    """
    trades = list(result.trades.all())
    timestamps = []
    for trade in trades:
        timestamps.append(trade.entered_at)
        if trade.exited_at:
            timestamps.append(trade.exited_at)

    sources_by_timestamp = {
        price.timestamp: price.source
        for price in PriceData.objects.filter(stock=result.stock, timestamp__in=timestamps)
    }
    issues = []
    for trade in trades:
        entry_source = sources_by_timestamp.get(trade.entered_at)
        exit_source = sources_by_timestamp.get(trade.exited_at)
        if entry_source and exit_source and entry_source != exit_source:
            issues.append(
                {
                    'trade': trade,
                    'entry_source': entry_source,
                    'exit_source': exit_source,
                }
            )
    return issues


@transaction.atomic
def run_backtest(user, strategy, start_date, end_date):
    """Run a strategy over old prices and save the result.

    Parameters:
        user: Owner of the saved result.
        strategy: Strategy settings to simulate.
        start_date/end_date: Requested date range.

    Returns:
        The created ``BacktestResult``. Related ``BacktestTrade`` rows are
        created before the result is returned.

    Raises:
        ValueError: if the selected date range has too little price history for
        the strategy's long moving-average window.
    """
    initial_balance = Decimal(strategy.initial_balance)
    if initial_balance <= Decimal('0'):
        raise ValueError('Initial balance must be positive to calculate returns.')

    prices = list(backtest_price_queryset(strategy.stock, start_date, end_date))
    if not prices:
        raise ValueError(
            f'No price history found for {strategy.stock.symbol} from {start_date} to {end_date}.'
        )
    if len(prices) < strategy.long_window:
        raise ValueError(
            f'Not enough price history for {strategy.stock.symbol} from {start_date} to {end_date}: '
            f'found {len(prices)} rows, need at least {strategy.long_window} for the long moving-average window.'
        )

    cash = initial_balance
    position_qty = Decimal('0')
    entry_price = None
    open_trade = None
    equity_curve = []
    peak_equity = initial_balance
    max_drawdown = Decimal('0')
    completed = []
    signals = generate_signals(strategy, prices)

    for item in signals:
        point = item['price']
        close = point.close_price
        # Risk exits are checked on every row while a position is open.
        stop_hit = entry_price and close <= entry_price * (Decimal('1') - strategy.stop_loss_percent / Decimal('100'))
        target_hit = entry_price and close >= entry_price * (Decimal('1') + strategy.take_profit_percent / Decimal('100'))

        if position_qty > 0 and (item['signal'] == 'sell' or stop_hit or target_hit):
            # Closing a position records P/L and why the trade exited.
            cash += position_qty * close
            pnl = (close - entry_price) * position_qty
            reason = 'stop_loss' if stop_hit else 'take_profit' if target_hit else 'signal'
            open_trade.exited_at = point.timestamp
            open_trade.exit_price = close
            open_trade.pnl = money(pnl)
            open_trade.exit_reason = reason
            completed.append(open_trade)
            position_qty = Decimal('0')
            entry_price = None
            open_trade = None
        elif position_qty == 0 and item['signal'] == 'buy':
            # Position size is a percent of available simulated cash.
            allocation = cash * strategy.position_size_percent / Decimal('100')
            if allocation > 0:
                position_qty = quantity(allocation / close)
                if position_qty > 0:
                    cash -= position_qty * close
                    entry_price = close
                    open_trade = BacktestTrade(
                        entered_at=point.timestamp,
                        entry_price=close,
                        quantity=position_qty,
                    )

        # Equity includes both cash and the current value of the open position.
        equity = cash + position_qty * close
        peak_equity = max(peak_equity, equity)
        if peak_equity:
            drawdown = (peak_equity - equity) / peak_equity * Decimal('100')
            max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append({'date': point.timestamp.date().isoformat(), 'equity': str(money(equity))})

    final_price = prices[-1].close_price
    if position_qty > 0 and open_trade:
        # Any open position is closed at the final price so the result has a
        # final balance and completed trade list.
        cash += position_qty * final_price
        pnl = (final_price - entry_price) * position_qty
        open_trade.exited_at = prices[-1].timestamp
        open_trade.exit_price = final_price
        open_trade.pnl = money(pnl)
        open_trade.exit_reason = 'end_of_test'
        completed.append(open_trade)

    final_balance = money(cash)
    total_return = percent(((final_balance - initial_balance) / initial_balance) * Decimal('100'))
    wins = sum(1 for trade in completed if trade.pnl > 0)
    losses = sum(1 for trade in completed if trade.pnl <= 0)
    completed_trades = len(completed)
    if completed_trades == 0:
        win_loss_ratio = percent(Decimal('0'))
    elif losses == 0:
        win_loss_ratio = percent(Decimal(wins))
    elif wins == 0:
        win_loss_ratio = percent(Decimal('0'))
    else:
        win_loss_ratio = percent(Decimal(wins) / Decimal(losses))

    result = BacktestResult.objects.create(
        user=user,
        strategy=strategy,
        stock=strategy.stock,
        start_date=prices[0].timestamp.date(),
        end_date=prices[-1].timestamp.date(),
        initial_balance=money(initial_balance),
        final_balance=final_balance,
        total_return=total_return,
        max_drawdown=percent(max_drawdown),
        number_of_trades=len(completed),
        win_loss_ratio=win_loss_ratio,
        equity_curve=equity_curve,
    )
    for trade in completed:
        trade.result = result
    # Trades are created in one batch after the result exists.
    BacktestTrade.objects.bulk_create(completed)
    return result
