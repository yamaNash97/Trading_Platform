from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from backtesting.models import BacktestResult
from paper_trading.models import Transaction
from paper_trading.services import get_or_create_account
from portfolio.models import PortfolioHolding


@login_required
def dashboard(request):
    account = get_or_create_account(request.user)
    holdings = list(PortfolioHolding.objects.filter(user=request.user).select_related('stock'))
    portfolio_value = sum((holding.market_value() for holding in holdings), Decimal('0'))
    unrealized_pnl = sum((holding.unrealized_pnl() for holding in holdings), Decimal('0'))
    recent_transactions = Transaction.objects.filter(user=request.user).select_related('stock')[:8]
    backtests = BacktestResult.objects.filter(user=request.user).select_related('strategy', 'stock')[:5]
    total_value = account.balance + portfolio_value
    return render(
        request,
        'portfolio/dashboard.html',
        {
            'account': account,
            'holdings': holdings,
            'portfolio_value': portfolio_value,
            'unrealized_pnl': unrealized_pnl,
            'recent_transactions': recent_transactions,
            'backtests': backtests,
            'total_value': total_value,
        },
    )

# Create your views here.
