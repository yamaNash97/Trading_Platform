from django.contrib import admin
from django.urls import include, path

# Root URL map delegates each feature area to its app-level urls.py.
urlpatterns = [
    path('admin/', admin.site.urls),
    # Custom signup plus Django's built-in login/logout/password routes.
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('market/', include('market_data.urls')),
    path('strategies/', include('strategies.urls')),
    path('backtests/', include('backtesting.urls')),
    path('paper/', include('paper_trading.urls')),
    path('', include('portfolio.urls')),
]
