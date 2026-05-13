from django.conf import settings
from django.db import models

from market_data.models import Stock


class Strategy(models.Model):
    """User-owned trading strategy configuration.

    A strategy stores the instrument, high-level strategy type, risk settings,
    and parameter JSON used by the signal engine. Backtests read these values to
    generate buy/sell/hold signals over historical ``PriceData`` rows.
    """

    class StrategyType(models.TextChoices):
        """Supported signal-generation modes."""

        MOVING_AVERAGE = 'moving_average', 'Moving Average Crossover'
        RSI = 'rsi', 'RSI Strategy'
        COMBINED = 'combined', 'Combined MA + RSI'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='strategies', on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, related_name='strategies', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    strategy_type = models.CharField(max_length=32, choices=StrategyType.choices)
    # JSON keeps strategy-specific knobs flexible without adding a migration for
    # every indicator parameter the form exposes.
    parameters = models.JSONField(default=dict, blank=True)
    # Decimal fields keep simulated money and percentages stable in backtests.
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
        """Return the short moving-average window with a safe default."""
        return int(self.parameters.get('short_window', 20))

    @property
    def long_window(self):
        """Return the long moving-average window with a safe default."""
        return int(self.parameters.get('long_window', 50))

    @property
    def rsi_period(self):
        """Return the RSI lookback period with a safe default."""
        return int(self.parameters.get('rsi_period', 14))

    @property
    def rsi_buy_threshold(self):
        """Return the RSI threshold used to trigger buy signals."""
        return int(self.parameters.get('rsi_buy_threshold', 30))

    @property
    def rsi_sell_threshold(self):
        """Return the RSI threshold used to trigger sell signals."""
        return int(self.parameters.get('rsi_sell_threshold', 70))
