from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from market_data.charting import chart_context
from strategies.models import Strategy

from .forms import BacktestRunForm
from .models import BacktestResult
from .services import run_backtest


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
    strategy_id = request.GET.get('strategy')
    if strategy_id and strategy_id.isdigit():
        strategy = strategies.filter(pk=strategy_id).first()
    if strategy is None:
        strategy = strategies.first()

    if strategy is None:
        chart = {'stock': None, 'has_data': False, 'warning': 'Create an active strategy to load a chart.'}
    else:
        chart = chart_context(strategy.stock, refresh_live=True)
    return render(request, 'market_data/_price_chart.html', {'chart': chart})


@login_required
def result_price_chart(request, pk):
    result = get_object_or_404(
        BacktestResult.objects.select_related('stock'),
        pk=pk,
        user=request.user,
    )
    chart = chart_context(
        result.stock,
        start_date=result.start_date,
        end_date=result.end_date,
        refresh_live=True,
    )
    return render(request, 'market_data/_price_chart.html', {'chart': chart})

# Create your views here.
