from decimal import Decimal

from django.conf import settings
from django.db import models

from market_data.models import Stock


class PortfolioHolding(models.Model):
    """A user's current paper-trading position in a single stock.

    Each row represents one user/stock pair and stores the share quantity plus
    the weighted average buy price used to estimate open gains or losses.
    Paper-trading fills update this model through
    ``paper_trading.services.execute_order``.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='holdings', on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, related_name='holdings', on_delete=models.CASCADE)
    # Decimal keeps holdings precise enough for fractional paper amounts.
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    average_buy_price = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['stock__symbol']
        constraints = [
            models.UniqueConstraint(fields=['user', 'stock'], name='unique_user_stock_holding')
        ]

    def market_value(self):
        """Return the holding's value using the latest saved close price."""
        latest = self.stock.price_data.order_by('-timestamp').first()
        return self.quantity * latest.close_price if latest else Decimal('0')

    def unrealized_pnl(self):
        """Return open profit/loss against the average buy price."""
        return self.market_value() - (self.quantity * self.average_buy_price)

    def __str__(self):
        return f'{self.user} {self.stock.symbol} {self.quantity}'
