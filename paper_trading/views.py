from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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

# Create your views here.
