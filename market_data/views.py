from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .charting import chart_context, chart_request_options
from .forms import StockForm
from .models import Stock
from .services import import_alpha_vantage_daily, import_default_commodities, seed_sample_prices


def chart_stock_options():
    """Return lightweight stock rows for chart selector dropdowns."""
    return Stock.objects.only('id', 'symbol', 'name').order_by('symbol')


def chart_with_stock_options(stock, request):
    """Build a chart context and attach stock-selector metadata."""
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
    without waiting for an external provider import.
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
    # Prefetch price_data because the table displays a row count for each stock.
    stocks = Stock.objects.prefetch_related('price_data')
    return render(request, 'market_data/stock_list.html', {'form': form, 'stocks': stocks})


@login_required
def import_commodities(request):
    """Import the default commodity set and redirect back to the stock list."""
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
    """Show one stock, recent raw prices, and the HTMX-loaded chart shell."""
    stock = get_object_or_404(Stock, pk=pk)
    # The table only previews recent rows; the reusable chart endpoint performs
    # its own timeframe filtering and JSON payload construction.
    prices = stock.price_data.order_by('-timestamp')[:90]
    return render(request, 'market_data/stock_detail.html', {'stock': stock, 'prices': prices})


@login_required
def stock_price_chart(request, pk):
    """Render a chart fragment for a stock-specific URL.

    This endpoint is useful for direct chart embeds that already know a stock
    primary key. The stock list/detail pages use ``stock_chart`` because it can
    also respond to dropdown changes via a query parameter.
    """
    stock = get_object_or_404(Stock, pk=pk)
    chart = chart_with_stock_options(stock, request)
    return render(request, 'market_data/_price_chart.html', {'chart': chart})


@login_required
def stock_chart(request):
    """Render the reusable market chart fragment for HTMX requests.

    The selected stock comes from ``?stock=``. When no valid stock is supplied,
    the view falls back to the first known stock so dashboard widgets can load a
    useful default.
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
    """Create deterministic sample price rows for a stock."""
    stock = get_object_or_404(Stock, pk=pk)
    created = seed_sample_prices(stock)
    messages.success(request, f'{created} sample price rows were created for {stock.symbol}.')
    return redirect('market_data:stock_detail', pk=stock.pk)


@login_required
def refresh_alpha_vantage(request, pk):
    """Refresh one stock from Alpha Vantage daily data."""
    stock = get_object_or_404(Stock, pk=pk)
    try:
        imported = import_alpha_vantage_daily(stock)
    except Exception as exc:
        messages.error(request, f'Could not refresh {stock.symbol}: {exc}')
    else:
        messages.success(request, f'{imported} new Alpha Vantage rows imported for {stock.symbol}.')
    return redirect('market_data:stock_detail', pk=stock.pk)
