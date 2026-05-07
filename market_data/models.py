from django.db import models


class Stock(models.Model):
    symbol = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=180)
    exchange = models.CharField(max_length=80, blank=True)
    currency = models.CharField(max_length=8, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']

    def save(self, *args, **kwargs):
        self.symbol = self.symbol.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.symbol} - {self.name}'


class PriceData(models.Model):
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
            models.UniqueConstraint(fields=['stock', 'timestamp'], name='unique_stock_price_timestamp')
        ]

    def __str__(self):
        return f'{self.stock.symbol} {self.timestamp:%Y-%m-%d} {self.close_price}'

# Create your models here.
