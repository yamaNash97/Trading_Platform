from django.conf import settings
from django.db import models

from market_data.models import Stock
from strategies.models import Strategy


class BacktestResult(models.Model):
    """Saved summary of one historical strategy simulation.

    A result belongs to a user and stores the strategy, stock, actual price
    range used, account numbers, and equity curve made by
    ``backtesting.services.run_backtest``.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='backtests', on_delete=models.CASCADE)
    strategy = models.ForeignKey(Strategy, related_name='backtests', on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, related_name='backtests', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    # Percentage fields are Decimal values so reports stay stable and sortable.
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2)
    final_balance = models.DecimalField(max_digits=14, decimal_places=2)
    total_return = models.DecimalField(max_digits=12, decimal_places=2)
    max_drawdown = models.DecimalField(max_digits=12, decimal_places=2)
    number_of_trades = models.PositiveIntegerField(default=0)
    win_loss_ratio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Stored as JSON so Chart.js can draw it on the detail page.
    equity_curve = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.strategy.name} on {self.stock.symbol}: {self.total_return}%'


class BacktestTrade(models.Model):
    """One completed trade created during a backtest."""

    result = models.ForeignKey(BacktestResult, related_name='trades', on_delete=models.CASCADE)
    entered_at = models.DateTimeField()
    exited_at = models.DateTimeField(null=True, blank=True)
    entry_price = models.DecimalField(max_digits=14, decimal_places=4)
    exit_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    # Six decimals allow fractional quantities from percentage sizing.
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    pnl = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    exit_reason = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['entered_at']
