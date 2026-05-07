from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from strategies.services import generate_signals

from .models import BacktestResult, BacktestTrade


def money(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def percent(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@transaction.atomic
def run_backtest(user, strategy, start_date, end_date):
    prices = list(
        strategy.stock.price_data.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date).order_by('timestamp')
    )
    if len(prices) < strategy.long_window:
        raise ValueError('Not enough price history for the selected strategy and date range.')

    cash = Decimal(strategy.initial_balance)
    initial_balance = Decimal(strategy.initial_balance)
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
        stop_hit = entry_price and close <= entry_price * (Decimal('1') - strategy.stop_loss_percent / Decimal('100'))
        target_hit = entry_price and close >= entry_price * (Decimal('1') + strategy.take_profit_percent / Decimal('100'))

        if position_qty > 0 and (item['signal'] == 'sell' or stop_hit or target_hit):
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
            allocation = cash * strategy.position_size_percent / Decimal('100')
            if allocation > 0:
                position_qty = allocation / close
                cash -= allocation
                entry_price = close
                open_trade = BacktestTrade(
                    entered_at=point.timestamp,
                    entry_price=close,
                    quantity=position_qty,
                )

        equity = cash + position_qty * close
        peak_equity = max(peak_equity, equity)
        if peak_equity:
            drawdown = (peak_equity - equity) / peak_equity * Decimal('100')
            max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append({'date': point.timestamp.date().isoformat(), 'equity': str(money(equity))})

    final_price = prices[-1].close_price
    if position_qty > 0 and open_trade:
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
    win_loss_ratio = percent(Decimal(wins) / Decimal(losses)) if losses else percent(wins)

    result = BacktestResult.objects.create(
        user=user,
        strategy=strategy,
        stock=strategy.stock,
        start_date=start_date,
        end_date=end_date,
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
    BacktestTrade.objects.bulk_create(completed)
    return result
