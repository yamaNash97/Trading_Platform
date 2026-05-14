from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from market_data.charting import chart_context, chart_request_options
from market_data.models import Stock
from strategies.models import Strategy

from .forms import BacktestRunForm
from .models import BacktestResult
from .services import run_backtest, trade_source_issues


def add_chart_stock_selector(chart, stock, selector_url):
    """Add stock dropdown data to a chart context."""
    chart['stock_options'] = Stock.objects.only('id', 'symbol', 'name').order_by('symbol')
    chart['selected_stock_id'] = stock.pk if stock else None
    chart['stock_selector_url'] = selector_url
    return chart


@login_required
def backtest_list(request):
    """Display the backtest launcher and the user's saved results."""
    if request.method == 'POST':
        form = BacktestRunForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                # The service owns the simulation math and saving; the view only
                # turns success or failure into messages and redirects.
                result = run_backtest(
                    request.user,
                    form.cleaned_data['strategy'],
                    form.cleaned_data['start_date'],
                    form.cleaned_data['end_date'],
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, 'Backtest completed.')
                return redirect('backtesting:backtest_detail', pk=result.pk)
    else:
        form = BacktestRunForm(user=request.user)
    # select_related keeps the results table from querying strategy/stock for
    # each row.
    results = BacktestResult.objects.filter(user=request.user).select_related('strategy', 'stock')
    return render(request, 'backtesting/backtest_list.html', {'form': form, 'results': results})


@login_required
def backtest_detail(request, pk):
    """Render one saved backtest result owned by the signed-in user."""
    result = get_object_or_404(
        BacktestResult.objects.select_related('strategy', 'stock').prefetch_related('trades'),
        pk=pk,
        user=request.user,
    )
    return render(request, 'backtesting/backtest_detail.html', {'result': result, 'trade_source_issues': trade_source_issues(result)})


@login_required
def strategy_price_chart(request):
    """Render the strategy preview chart used by the backtest form.

    The chart can use either a selected strategy or a selected stock. Stock
    choice wins because the chart dropdown sends a ``stock`` query parameter.
    """
    strategies = Strategy.objects.filter(user=request.user, is_active=True).select_related('stock')
    strategy = None
    stock = None
    stock_id = request.GET.get('stock')
    if stock_id and stock_id.isdigit():
        stock = Stock.objects.filter(pk=stock_id).first()

    strategy_id = request.GET.get('strategy')
    if stock is None and strategy_id and strategy_id.isdigit():
        strategy = strategies.filter(pk=strategy_id).first()
    if stock is None and strategy is None:
        strategy = strategies.first()
    if stock is None and strategy is not None:
        stock = strategy.stock

    if stock is None:
        chart = {
            'stock': None,
            'has_data': False,
            'warning': 'Add a stock or create an active strategy to load a chart.',
            'stock_options': Stock.objects.only('id', 'symbol', 'name').order_by('symbol'),
            'stock_selector_url': reverse('backtesting:strategy_price_chart'),
        }
    else:
        # Preview charts try a live refresh but still show saved data if the API
        # is not available.
        chart = chart_context(stock, **chart_request_options(request, default_refresh_live=True))
        add_chart_stock_selector(chart, stock, reverse('backtesting:strategy_price_chart'))
    return render(request, 'market_data/_price_chart.html', {'chart': chart})


@login_required
def result_price_chart(request, pk):
    """Render the historical chart for a saved backtest result.

    This chart is locked to the result's stock and date range. It ignores live
    refresh so the report can be viewed the same way later.
    """
    result = get_object_or_404(
        BacktestResult.objects.select_related('stock'),
        pk=pk,
        user=request.user,
    )
    options = chart_request_options(request, default_refresh_live=False, default_timeframe=None)

    # Date bounds come from the saved result, not request values.
    chart = chart_context(
        result.stock,
        start_date=result.start_date,
        end_date=result.end_date,
        refresh_live=False,
        timeframe=options['timeframe'],
    )
    chart['live_refresh_enabled'] = False
    return render(request, 'market_data/_price_chart.html', {'chart': chart})
