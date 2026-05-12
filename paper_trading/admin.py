from django.contrib import admin

from .models import Order, PaperAccount, Transaction


@admin.register(PaperAccount)
class PaperAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'starting_balance', 'updated_at')
    search_fields = ('user__username',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'stock', 'order_type', 'quantity', 'price', 'status', 'created_at')
    list_filter = ('status', 'order_type')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'stock', 'transaction_type', 'quantity', 'price', 'created_at')
    list_filter = ('transaction_type',)
