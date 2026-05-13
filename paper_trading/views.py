from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from market_data.charting import chart_context, chart_request_options
from market_data.models import Stock

from .forms import OrderForm
from .models import Order, Transaction
from .services import execute_order, get_or_create_account


@login_required
def paper_account(request):
    """Show the paper account and handle order placement.

    POST requests validate the form, attach the signed-in user, and delegate all
    execution decisions to ``execute_order``. The view only translates the final
    order status into success/error messages for the user.
    """
    account = get_or_create_account(request.user)
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order = execute_order(order)
            if order.status == Order.Status.FILLED:
                messages.success(request, f'{order.get_order_type_display()} order filled at {order.price}.')
            else:
                messages.error(request, order.rejection_reason)
            return redirect('paper_trading:paper_account')
    else:
        form = OrderForm()
    # Recent orders and transactions are displayed as compact activity tables.
    orders = Order.objects.filter(user=request.user).select_related('stock')[:20]
    transactions = Transaction.objects.filter(user=request.user).select_related('stock')[:20]
    return render(
        request,
        'paper_trading/paper_account.html',
        {'account': account, 'form': form, 'orders': orders, 'transactions': transactions},
    )


@login_required
def price_chart(request):
    """Render the HTMX chart fragment used beside the order form."""
    stock = None
    stock_id = request.GET.get('stock')
    if stock_id and stock_id.isdigit():
        stock = Stock.objects.filter(pk=stock_id).first()
    if stock is None:
        stock = Stock.objects.order_by('symbol').first()

    if stock is None:
        chart = {'stock': None, 'has_data': False, 'warning': 'Add a stock before loading the paper trading chart.'}
    else:
        # The paper-trading chart defaults to live refresh because it supports
        # immediate order decisions, but still falls back to saved prices.
        chart = chart_context(stock, **chart_request_options(request, default_refresh_live=True))
        chart['stock_options'] = Stock.objects.only('id', 'symbol', 'name').order_by('symbol')
        chart['selected_stock_id'] = stock.pk
        chart['stock_selector_url'] = reverse('paper_trading:price_chart')
    return render(request, 'market_data/_price_chart.html', {'chart': chart})
