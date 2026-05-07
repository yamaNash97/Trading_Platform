from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from market_data.services import latest_price
from portfolio.models import PortfolioHolding

from .models import Order, PaperAccount, Transaction


def get_or_create_account(user):
    return PaperAccount.objects.get_or_create(user=user)[0]


@transaction.atomic
def execute_order(order):
    account = get_or_create_account(order.user)
    price = latest_price(order.stock)
    if price <= 0:
        order.status = Order.Status.REJECTED
        order.rejection_reason = 'No latest market price is available.'
        order.save()
        return order

    order.price = price
    cost = order.quantity * price
    holding, _ = PortfolioHolding.objects.select_for_update().get_or_create(user=order.user, stock=order.stock)

    if order.order_type == Order.OrderType.BUY:
        if account.balance < cost:
            order.status = Order.Status.REJECTED
            order.rejection_reason = 'Insufficient virtual cash.'
            order.save()
            return order
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
        if holding.quantity == 0:
            holding.average_buy_price = Decimal('0')

    holding.save()
    account.save(update_fields=['balance', 'updated_at'])
    order.status = Order.Status.FILLED
    order.filled_at = timezone.now()
    order.save()
    Transaction.objects.create(
        user=order.user,
        order=order,
        stock=order.stock,
        quantity=order.quantity,
        price=price,
        transaction_type=order.order_type,
    )
    return order
