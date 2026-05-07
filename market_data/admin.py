from django.contrib import admin

from .models import PriceData, Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'exchange', 'currency', 'updated_at')
    search_fields = ('symbol', 'name', 'exchange')


@admin.register(PriceData)
class PriceDataAdmin(admin.ModelAdmin):
    list_display = ('stock', 'timestamp', 'open_price', 'close_price', 'volume', 'source')
    list_filter = ('source', 'stock')
    search_fields = ('stock__symbol',)

# Register your models here.
