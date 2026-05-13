from django.contrib import admin

from .models import BacktestResult, BacktestTrade


class BacktestTradeInline(admin.TabularInline):
    """Inline trade rows shown on a saved backtest result."""

    model = BacktestTrade
    extra = 0


@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    """Admin list configuration for saved backtest results."""

    list_display = ('strategy', 'stock', 'user', 'total_return', 'max_drawdown', 'number_of_trades', 'created_at')
    list_filter = ('stock', 'created_at')
    inlines = [BacktestTradeInline]
