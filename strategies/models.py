from django.conf import settings
from django.db import models

from market_data.models import Stock


class Strategy(models.Model):
    class StrategyType(models.TextChoices):
        MOVING_AVERAGE = 'moving_average', 'Moving Average Crossover'
        RSI = 'rsi', 'RSI Strategy'
        COMBINED = 'combined', 'Combined MA + RSI'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='strategies', on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, related_name='strategies', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    strategy_type = models.CharField(max_length=32, choices=StrategyType.choices)
    parameters = models.JSONField(default=dict, blank=True)
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=10000)
    position_size_percent = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    stop_loss_percent = models.DecimalField(max_digits=5, decimal_places=2, default=8)
    take_profit_percent = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.get_strategy_type_display()})'

    @property
    def short_window(self):
        return int(self.parameters.get('short_window', 20))

    @property
    def long_window(self):
        return int(self.parameters.get('long_window', 50))

    @property
    def rsi_period(self):
        return int(self.parameters.get('rsi_period', 14))

    @property
    def rsi_buy_threshold(self):
        return int(self.parameters.get('rsi_buy_threshold', 30))

    @property
    def rsi_sell_threshold(self):
        return int(self.parameters.get('rsi_sell_threshold', 70))

# Create your models here.
