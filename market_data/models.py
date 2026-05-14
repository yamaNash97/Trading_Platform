from django.db import models


class Stock(models.Model):
    """Tradable item tracked by the simulator.

    ``symbol`` is unique because each price row, strategy, order, and holding
    links back to one stock. ``exchange`` and ``currency`` are simple strings so
    stocks, indices, and commodities can share this model.
    """

    symbol = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=180)
    exchange = models.CharField(max_length=80, blank=True)
    currency = models.CharField(max_length=8, default='USD')
    # These dates show when the stock row was created or last changed.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']

    def save(self, *args, **kwargs):
        """Store ticker symbols in uppercase."""
        self.symbol = self.symbol.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.symbol} - {self.name}'


class PriceData(models.Model):
    """One OHLCV market data point for a stock.

    The simulator stores decimal prices to avoid float rounding issues in
    trading math. ``source`` shows whether a row came from sample data,
    yfinance, Alpha Vantage stocks, or Alpha Vantage commodities.
    """

    stock = models.ForeignKey(Stock, related_name='price_data', on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    open_price = models.DecimalField(max_digits=14, decimal_places=4)
    high_price = models.DecimalField(max_digits=14, decimal_places=4)
    low_price = models.DecimalField(max_digits=14, decimal_places=4)
    close_price = models.DecimalField(max_digits=14, decimal_places=4)
    volume = models.BigIntegerField(default=0)
    source = models.CharField(max_length=40, default='manual')

    class Meta:
        ordering = ['timestamp']
        constraints = [
            # A refresh can see the same timestamp again, so update the old row
            # instead of creating a duplicate.
            models.UniqueConstraint(fields=['stock', 'timestamp'], name='unique_stock_price_timestamp')
        ]

    def __str__(self):
        return f'{self.stock.symbol} {self.timestamp:%Y-%m-%d} {self.close_price}'
