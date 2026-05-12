from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from market_data.charting import chart_context, chart_request_options
from market_data.models import Stock
from strategies.models import Strategy

from .forms import BacktestRunForm
from .models import BacktestResult
from .services import run_backtest


def add_chart_stock_selector(chart, stock, selector_url):
    chart['stock_options'] = Stock.objects.only('id', 'symbol', 'name').order_by('symbol')
    chart['selected_stock_id'] = stock.pk if stock else None
    chart['stock_selector_url'] = selector_url
    return chart


@login_required
def backtest_list(request):
    if request.method == 'POST':
        form = BacktestRunForm(request.POST, user=request.user)
        if form.is_valid():
            try:
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
    results = BacktestResult.objects.filter(user=request.user).select_related('strategy', 'stock')
    return render(request, 'backtesting/backtest_list.html', {'form': form, 'results': results})


@login_required
def backtest_detail(request, pk):
    result = get_object_or_404(
        BacktestResult.objects.select_related('strategy', 'stock').prefetch_related('trades'),
        pk=pk,
        user=request.user,
    )
    return render(request, 'backtesting/backtest_detail.html', {'result': result})


@login_required
def strategy_price_chart(request):
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
        chart = chart_context(stock, **chart_request_options(request, default_refresh_live=True))
        add_chart_stock_selector(chart, stock, reverse('backtesting:strategy_price_chart'))
    return render(request, 'market_data/_price_chart.html', {'chart': chart})


@login_required
def result_price_chart(request, pk):
    result = get_object_or_404(
        BacktestResult.objects.select_related('stock'),
        pk=pk,
        user=request.user,
    )
    stock = result.stock
    stock_id = request.GET.get('stock')
    if stock_id and stock_id.isdigit():
        stock = Stock.objects.filter(pk=stock_id).first() or result.stock

    chart = chart_context(
        stock,
        start_date=result.start_date,
        end_date=result.end_date,
        **chart_request_options(request, default_refresh_live=True),
    )
    add_chart_stock_selector(chart, stock, reverse('backtesting:result_price_chart', kwargs={'pk': result.pk}))
    return render(request, 'market_data/_price_chart.html', {'chart': chart})
