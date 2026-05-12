from decimal import Decimal

from django.conf import settings
from django.db import models

from market_data.models import Stock


class PortfolioHolding(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='holdings', on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, related_name='holdings', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    average_buy_price = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['stock__symbol']
        constraints = [
            models.UniqueConstraint(fields=['user', 'stock'], name='unique_user_stock_holding')
        ]

    def market_value(self):
        latest = self.stock.price_data.order_by('-timestamp').first()
        return self.quantity * latest.close_price if latest else Decimal('0')

    def unrealized_pnl(self):
        return self.market_value() - (self.quantity * self.average_buy_price)

    def __str__(self):
        return f'{self.user} {self.stock.symbol} {self.quantity}'
