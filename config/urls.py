from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('market/', include('market_data.urls')),
    path('strategies/', include('strategies.urls')),
    path('backtests/', include('backtesting.urls')),
    path('paper/', include('paper_trading.urls')),
    path('', include('portfolio.urls')),
]
