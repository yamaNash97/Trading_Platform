from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from market_data.charting import chart_context, chart_request_options
from market_data.models import Stock

from .forms import OrderForm
from .models import Order, Transaction
from .services import execute_order, get_or_create_account


@login_required
def paper_account(request):
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
    orders = Order.objects.filter(user=request.user).select_related('stock')[:20]
    transactions = Transaction.objects.filter(user=request.user).select_related('stock')[:20]
    return render(
        request,
        'paper_trading/paper_account.html',
        {'account': account, 'form': form, 'orders': orders, 'transactions': transactions},
    )


@login_required
def price_chart(request):
    stock = None
    stock_id = request.GET.get('stock')
    if stock_id and stock_id.isdigit():
        stock = Stock.objects.filter(pk=stock_id).first()
    if stock is None:
        stock = Stock.objects.order_by('symbol').first()

    if stock is None:
        chart = {'stock': None, 'has_data': False, 'warning': 'Add a stock before loading the paper trading chart.'}
    else:
        chart = chart_context(stock, **chart_request_options(request, default_refresh_live=True))
    return render(request, 'market_data/_price_chart.html', {'chart': chart})

# Create your views here.
