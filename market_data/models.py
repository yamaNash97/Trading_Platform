from django.db import models


class Stock(models.Model):
    """Tradable instrument tracked by the simulator.

    ``symbol`` is unique because every related price row, strategy, order, and
    holding resolves back to this canonical instrument. ``exchange`` and
    ``currency`` are intentionally lightweight strings so equities, indices,
    and commodities can share the same model without a separate lookup table.
    """

    symbol = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=180)
    exchange = models.CharField(max_length=80, blank=True)
    currency = models.CharField(max_length=8, default='USD')
    # Audit timestamps help identify when a market instrument was created or
    # last touched without changing the price-history records themselves.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']

    def save(self, *args, **kwargs):
        """Store ticker symbols in the normalized uppercase format."""
        self.symbol = self.symbol.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.symbol} - {self.name}'


class PriceData(models.Model):
    """One OHLCV market data point for a stock.

    The simulator stores decimal prices to avoid binary floating-point drift in
    trading calculations. ``source`` records whether a row came from sample
    data, yfinance, Alpha Vantage equities, or Alpha Vantage commodities.
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
            # A provider can refresh the same timestamp, but it should update
            # the existing row instead of creating duplicates.
            models.UniqueConstraint(fields=['stock', 'timestamp'], name='unique_stock_price_timestamp')
        ]

    def __str__(self):
        return f'{self.stock.symbol} {self.timestamp:%Y-%m-%d} {self.close_price}'
