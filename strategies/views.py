from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import StrategyForm
from .models import Strategy


@login_required
def strategy_list(request):
    """Render the signed-in user's strategy list."""
    # select_related avoids one stock lookup per row in the strategy table.
    strategies = Strategy.objects.filter(user=request.user).select_related('stock')
    return render(request, 'strategies/strategy_list.html', {'strategies': strategies})


@login_required
def strategy_create(request):
    """Create a new strategy for the signed-in user."""
    if request.method == 'POST':
        form = StrategyForm(request.POST)
        if form.is_valid():
            strategy = form.save(commit=False)
            # The user is set on the server so a submitted form cannot create
            # a strategy for another account.
            strategy.user = request.user
            strategy.save()
            messages.success(request, f'{strategy.name} was created.')
            return redirect('strategies:strategy_detail', pk=strategy.pk)
    else:
        form = StrategyForm()
    return render(request, 'strategies/strategy_form.html', {'form': form})


@login_required
def strategy_detail(request, pk):
    """Render one strategy owned by the signed-in user."""
    strategy = get_object_or_404(Strategy.objects.select_related('stock'), pk=pk, user=request.user)
    return render(request, 'strategies/strategy_detail.html', {'strategy': strategy})
