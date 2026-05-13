from django.conf import settings
from django.db import models

from market_data.models import Stock


class PaperAccount(models.Model):
    """Virtual cash account used for simulated trading.

    Each user has one paper account. ``starting_balance`` records the original
    funding amount, while ``balance`` changes as buy and sell orders are filled.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='paper_account', on_delete=models.CASCADE)
    starting_balance = models.DecimalField(max_digits=14, decimal_places=2, default=100000)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=100000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} paper account'


class Order(models.Model):
    """A simulated order submitted by a user.

    Orders are created in ``pending`` status, then ``execute_order`` either
    fills them at the latest saved market price or rejects them with a reason.
    """

    class OrderType(models.TextChoices):
        """Supported trade directions."""

        BUY = 'buy', 'Buy'
        SELL = 'sell', 'Sell'

    class Status(models.TextChoices):
        """Lifecycle states for a paper order."""

        PENDING = 'pending', 'Pending'
        FILLED = 'filled', 'Filled'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, related_name='orders', on_delete=models.CASCADE)
    order_type = models.CharField(max_length=8, choices=OrderType.choices)
    quantity = models.DecimalField(max_digits=18, decimal_places=2)
    # price is populated at execution time from the latest PriceData close.
    price = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    filled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_order_type_display()} {self.quantity} {self.stock.symbol}'


class Transaction(models.Model):
    """Immutable ledger entry created for each filled paper order.

    Transactions preserve the executed quantity and price even if the source
    order is later removed, which is why ``order`` is nullable with SET_NULL.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transactions', on_delete=models.CASCADE)
    order = models.ForeignKey(Order, related_name='transactions', null=True, blank=True, on_delete=models.SET_NULL)
    stock = models.ForeignKey(Stock, related_name='transactions', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=18, decimal_places=2)
    price = models.DecimalField(max_digits=14, decimal_places=4)
    transaction_type = models.CharField(max_length=8, choices=Order.OrderType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
