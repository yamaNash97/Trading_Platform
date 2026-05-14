from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from market_data.charting import chart_context, chart_request_options
from market_data.models import Stock

from .forms import OrderForm
from .models import Order, Transaction
from .services import execute_order, exit_position, get_or_create_account, open_trade_rows


@login_required
def paper_account(request):
    """Show the paper account and handle order placement.

    POST requests check the form, attach the signed-in user, and send all
    order checks to ``execute_order``. The view only turns the final order
    status into success or error messages for the user.
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
    open_trades, refresh_warnings = open_trade_rows(request.user)
    # Recent orders and transactions are shown as small activity tables.
    orders = Order.objects.filter(user=request.user).select_related('stock')[:20]
    transactions = Transaction.objects.filter(user=request.user).select_related('stock')[:20]
    return render(
        request,
        'paper_trading/paper_account.html',
        {
            'account': account,
            'form': form,
            'open_trades': open_trades,
            'refresh_warnings': refresh_warnings,
            'orders': orders,
            'transactions': transactions,
        },
    )


@login_required
def open_trades(request):
    """Render the open-trade table, optionally refreshing live prices first."""
    rows, warnings = open_trade_rows(request.user, refresh_live=request.GET.get('refresh') == '1')
    return render(request, 'paper_trading/_open_trades.html', {'open_trades': rows, 'refresh_warnings': warnings})


@login_required
@require_POST
def exit_trade(request, stock_id):
    """Close the user's full open position for one stock."""
    stock = get_object_or_404(Stock, pk=stock_id)
    try:
        order, realized_pnl = exit_position(request.user, stock)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        if order.status == Order.Status.FILLED:
            result = 'made' if realized_pnl >= 0 else 'lost'
            messages.success(
                request,
                f'Exited {stock.symbol} at {order.price}. You {result} ${abs(realized_pnl):.2f}.',
            )
        else:
            messages.error(request, order.rejection_reason)
    return redirect('paper_trading:paper_account')


@login_required
def price_chart(request):
    """Render the HTMX chart HTML used beside the order form."""
    stock = None
    stock_id = request.GET.get('stock')
    if stock_id and stock_id.isdigit():
        stock = Stock.objects.filter(pk=stock_id).first()
    if stock is None:
        stock = Stock.objects.order_by('symbol').first()

    if stock is None:
        chart = {'stock': None, 'has_data': False, 'warning': 'Add a stock before loading the paper trading chart.'}
    else:
        # The paper-trading chart tries live refresh because it helps order
        # choices, but it still falls back to saved prices.
        chart = chart_context(stock, **chart_request_options(request, default_refresh_live=True))
        chart['stock_options'] = Stock.objects.only('id', 'symbol', 'name').order_by('symbol')
        chart['selected_stock_id'] = stock.pk
        chart['stock_selector_url'] = reverse('paper_trading:price_chart')
    return render(request, 'market_data/_price_chart.html', {'chart': chart})
