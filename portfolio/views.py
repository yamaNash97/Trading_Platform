from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from backtesting.models import BacktestResult
from paper_trading.models import Transaction
from paper_trading.services import get_or_create_account
from portfolio.models import PortfolioHolding


def landing(request):
    """Render the public marketing page.

    The landing template is static and does not require market data context.
    Keeping this view lean avoids querying commodity prices that are not
    displayed anywhere in the page.
    """
    return render(request, 'landing/index.html')


@login_required
def dashboard(request):
    """Render the logged-in portfolio dashboard.

    The view gets the current paper account, open holdings, recent transactions,
    and recent backtests for the signed-in user. Totals are calculated in Python
    because they combine account cash with holding methods that look up the
    latest saved market price.
    """
    account = get_or_create_account(request.user)
    # select_related keeps each table row from doing an extra stock query.
    holdings = list(PortfolioHolding.objects.filter(user=request.user).select_related('stock'))
    portfolio_value = sum((holding.market_value() for holding in holdings), Decimal('0'))
    unrealized_pnl = sum((holding.unrealized_pnl() for holding in holdings), Decimal('0'))
    # The dashboard only needs small recent activity lists.
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
