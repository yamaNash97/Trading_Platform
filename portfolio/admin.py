from django.contrib import admin

from .models import PortfolioHolding


@admin.register(PortfolioHolding)
class PortfolioHoldingAdmin(admin.ModelAdmin):
    list_display = ('user', 'stock', 'quantity', 'average_buy_price', 'updated_at')
    search_fields = ('user__username', 'stock__symbol')

# Register your models here.
