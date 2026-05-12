from django.contrib import admin

from .models import Strategy


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'stock', 'strategy_type', 'is_active', 'updated_at')
    list_filter = ('strategy_type', 'is_active')
    search_fields = ('name', 'stock__symbol', 'user__username')
