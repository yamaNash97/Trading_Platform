"""Paper-trading account and order services.

Views create unsaved ``Order`` instances from forms, then pass them here for
checks and filling. This module is the one place that changes virtual cash,
holdings, order statuses, and transaction rows.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from market_data.services import latest_price
from portfolio.models import PortfolioHolding

from .models import Order, PaperAccount, Transaction


def get_or_create_account(user):
    """Return the user's paper account, creating the default account if needed."""
    return PaperAccount.objects.get_or_create(user=user)[0]


def open_trade_rows(user, refresh_live=False):
    """Return valued open positions for the paper-trading screen.

    Filled buy orders are represented by positive ``PortfolioHolding`` rows.
    This helper turns those rows into display-ready trade values using the
    latest saved price, optionally trying a yfinance refresh first.
    """
    holdings = PortfolioHolding.objects.filter(user=user, quantity__gt=0).select_related('stock')
    rows = []
    warnings = []

    for holding in holdings:
        if refresh_live:
            try:
                from market_data.charting import refresh_yfinance_prices

                refresh_yfinance_prices(holding.stock)
            except Exception as exc:
                warnings.append(f'{holding.stock.symbol}: {exc}')

        current_price = latest_price(holding.stock)
        cost_basis = holding.quantity * holding.average_buy_price
        market_value = holding.quantity * current_price
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_percent = Decimal('0')
        if cost_basis:
            unrealized_pnl_percent = (unrealized_pnl / cost_basis) * Decimal('100')

        rows.append(
            {
                'holding': holding,
                'stock': holding.stock,
                'quantity': holding.quantity,
                'entry_price': holding.average_buy_price,
                'current_price': current_price,
                'cost_basis': cost_basis,
                'market_value': market_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_percent': unrealized_pnl_percent,
            }
        )

    return rows, warnings


@transaction.atomic
def execute_order(order):
    """Check and fill a paper-trading order.

    The order is filled at the latest saved close price for its stock. Buy
    orders need enough virtual cash; sell orders need enough shares in
    ``PortfolioHolding``. Rejected orders are saved with a clear reason.

    Returns:
        The saved ``Order`` with final status, price, and filled time when used.
    """
    account = get_or_create_account(order.user)
    price = latest_price(order.stock)
    if price <= 0:
        order.status = Order.Status.REJECTED
        order.rejection_reason = 'No latest market price is available.'
        order.save()
        return order

    order.price = price
    cost = order.quantity * price
    # Lock the holding row while filling the order so two requests cannot sell
    # or spend the same paper position at the same time.
    holding, _ = PortfolioHolding.objects.select_for_update().get_or_create(user=order.user, stock=order.stock)

    if order.order_type == Order.OrderType.BUY:
        if account.balance < cost:
            order.status = Order.Status.REJECTED
            order.rejection_reason = 'Insufficient virtual cash.'
            order.save()
            return order
        # Weighted average cost keeps unrealized P/L correct after buys at
        # different prices.
        previous_cost = holding.quantity * holding.average_buy_price
        holding.quantity += order.quantity
        holding.average_buy_price = (previous_cost + cost) / holding.quantity
        account.balance -= cost
    else:
        if holding.quantity < order.quantity:
            order.status = Order.Status.REJECTED
            order.rejection_reason = 'Insufficient shares in portfolio.'
            order.save()
            return order
        holding.quantity -= order.quantity
        account.balance += cost
        # Reset the cost basis when the user fully exits the position.
        if holding.quantity == 0:
            holding.average_buy_price = Decimal('0')

    holding.save()
    account.save(update_fields=['balance', 'updated_at'])
    order.status = Order.Status.FILLED
    order.filled_at = timezone.now()
    order.save()
    # A transaction records the fill details used by dashboards.
    Transaction.objects.create(
        user=order.user,
        order=order,
        stock=order.stock,
        quantity=order.quantity,
        price=price,
        transaction_type=order.order_type,
    )
    return order


@transaction.atomic
def exit_position(user, stock):
    """Sell the user's full open position and return realized P/L.

    The sale uses the same order execution path as manual sell orders, so cash,
    holdings, transactions, and order history are updated in one place.
    """
    holding = PortfolioHolding.objects.select_for_update().filter(user=user, stock=stock, quantity__gt=0).first()
    if holding is None:
        raise ValueError(f'No open {stock.symbol} position to exit.')

    entry_price = holding.average_buy_price
    quantity = holding.quantity
    order = Order(user=user, stock=stock, order_type=Order.OrderType.SELL, quantity=quantity)
    order = execute_order(order)
    realized_pnl = None
    if order.status == Order.Status.FILLED:
        realized_pnl = (order.price - entry_price) * quantity
    return order, realized_pnl
