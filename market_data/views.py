from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .charting import chart_context, chart_request_options
from .forms import StockForm
from .models import Stock
from .services import (
    import_alpha_vantage_commodity,
    import_alpha_vantage_daily,
    import_default_commodities,
    is_alpha_vantage_commodity_symbol,
    seed_sample_prices,
)


def chart_stock_options():
    """Return small stock rows for chart dropdowns."""
    return Stock.objects.only('id', 'symbol', 'name').order_by('symbol')


def chart_with_stock_options(stock, request):
    """Build a chart context and add stock dropdown data."""
    chart = chart_context(stock, **chart_request_options(request))
    chart['stock_options'] = chart_stock_options()
    chart['selected_stock_id'] = stock.pk
    chart['stock_selector_url'] = reverse('market_data:stock_chart')
    return chart


@login_required
def stock_list(request):
    """Display stocks and handle creation of a new seeded stock.

    POST requests create a ``Stock`` from ``StockForm`` and immediately seed
    sample OHLCV rows so charts, strategies, and paper trading can be used
    without waiting for an API import.
    """
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            stock = form.save()
            seed_sample_prices(stock)
            messages.success(request, f'{stock.symbol} was added with sample price history.')
            return redirect('market_data:stock_detail', pk=stock.pk)
    else:
        form = StockForm()
    # Prefetch price_data because the table shows a row count for each stock.
    stocks = Stock.objects.prefetch_related('price_data')
    return render(request, 'market_data/stock_list.html', {'form': form, 'stocks': stocks})


@login_required
def import_commodities(request):
    """Import the default commodity set and redirect back to the stock list."""
    if request.method != 'POST':
        messages.info(request, 'Use the Import commodities button to start the import.')
        return redirect('market_data:stock_list')

    try:
        results = import_default_commodities()
    except OperationalError:
        messages.error(request, 'The local database is busy. Please try importing commodities again in a moment.')
    except Exception as exc:
        messages.error(request, f'Could not import commodities: {exc}')
    else:
        summary = ', '.join(f'{stock.symbol}: {imported}' for stock, imported in results)
        messages.success(request, f'Commodity import complete. New rows: {summary}.')
    return redirect('market_data:stock_list')


@login_required
def stock_detail(request, pk):
    """Show one stock, recent prices, and the HTMX-loaded chart area."""
    stock = get_object_or_404(Stock, pk=pk)
    # The table shows recent rows only; the chart view does its own filtering
    # and JSON building.
    prices = stock.price_data.order_by('-timestamp')[:90]
    return render(request, 'market_data/stock_detail.html', {'stock': stock, 'prices': prices})


@login_required
def stock_chart(request):
    """Render reusable market chart HTML for HTMX requests.

    The selected stock comes from ``?stock=``. When no valid stock is supplied,
    the view uses the first known stock as a useful default.
    """
    stock = None
    stock_id = request.GET.get('stock')
    if stock_id and stock_id.isdigit():
        stock = Stock.objects.filter(pk=stock_id).first()
    if stock is None:
        stock = Stock.objects.order_by('symbol').first()

    if stock is None:
        chart = {
            'stock': None,
            'has_data': False,
            'warning': 'Add a stock before loading the market chart.',
            'stock_options': Stock.objects.none(),
        }
    else:
        chart = chart_with_stock_options(stock, request)
    return render(request, 'market_data/_price_chart.html', {'chart': chart})


@login_required
def seed_prices(request, pk):
    """Create repeatable sample price rows for a stock."""
    stock = get_object_or_404(Stock, pk=pk)
    if request.method != 'POST':
        messages.info(request, 'Use the Seed sample button to add demo price history.')
        return redirect('market_data:stock_detail', pk=stock.pk)

    try:
        created = seed_sample_prices(stock)
    except OperationalError:
        messages.error(request, 'The local database is busy. Please try seeding again in a moment.')
    else:
        messages.success(request, f'{created} sample price rows were created for {stock.symbol}.')
    return redirect('market_data:stock_detail', pk=stock.pk)


@login_required
def refresh_alpha_vantage(request, pk):
    """Refresh one stock or supported commodity from free Alpha Vantage data."""
    stock = get_object_or_404(Stock, pk=pk)
    try:
        if is_alpha_vantage_commodity_symbol(stock.symbol):
            _, imported = import_alpha_vantage_commodity(stock.symbol, stock=stock)
            source_label = 'commodity'
        else:
            imported = import_alpha_vantage_daily(stock)
            source_label = 'daily stock'
    except Exception as exc:
        messages.error(request, f'Could not refresh {stock.symbol}: {exc}')
    else:
        messages.success(request, f'{imported} new free Alpha Vantage {source_label} rows imported for {stock.symbol}.')
    return redirect('market_data:stock_detail', pk=stock.pk)
