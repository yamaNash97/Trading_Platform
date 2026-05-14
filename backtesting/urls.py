from django.urls import path

from . import views

app_name = 'backtesting'

# Backtesting has result pages plus chart-only HTMX URLs.
urlpatterns = [
    path('', views.backtest_list, name='backtest_list'),
    path('chart/', views.strategy_price_chart, name='strategy_price_chart'),
    path('<int:pk>/', views.backtest_detail, name='backtest_detail'),
    path('<int:pk>/chart/', views.result_price_chart, name='result_price_chart'),
]
