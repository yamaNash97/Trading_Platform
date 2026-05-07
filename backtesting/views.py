from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

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

# Create your views here.
