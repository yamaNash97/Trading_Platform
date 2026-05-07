from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StockForm
from .models import Stock
from .services import import_alpha_vantage_daily, import_default_commodities, seed_sample_prices


@login_required
def stock_list(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            stock = form.save()
            seed_sample_prices(stock)
            messages.success(request, f'{stock.symbol} was added with sample price history.')
            return redirect('market_data:stock_detail', pk=stock.pk)
    else:
        form = StockForm()
    stocks = Stock.objects.prefetch_related('price_data')
    return render(request, 'market_data/stock_list.html', {'form': form, 'stocks': stocks})


@login_required
def import_commodities(request):
    try:
        results = import_default_commodities()
    except Exception as exc:
        messages.error(request, f'Could not import commodities: {exc}')
    else:
        summary = ', '.join(f'{stock.symbol}: {imported}' for stock, imported in results)
        messages.success(request, f'Commodity import complete. New rows: {summary}.')
    return redirect('market_data:stock_list')


@login_required
def stock_detail(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    prices = stock.price_data.order_by('-timestamp')[:90]
    return render(request, 'market_data/stock_detail.html', {'stock': stock, 'prices': prices})


@login_required
def seed_prices(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    created = seed_sample_prices(stock)
    messages.success(request, f'{created} sample price rows were created for {stock.symbol}.')
    return redirect('market_data:stock_detail', pk=stock.pk)


@login_required
def refresh_alpha_vantage(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    try:
        imported = import_alpha_vantage_daily(stock)
    except Exception as exc:
        messages.error(request, f'Could not refresh {stock.symbol}: {exc}')
    else:
        messages.success(request, f'{imported} new Alpha Vantage rows imported for {stock.symbol}.')
    return redirect('market_data:stock_detail', pk=stock.pk)

# Create your views here.
