from django.urls import path

from . import views

app_name = 'paper_trading'

urlpatterns = [
    path('', views.paper_account, name='paper_account'),
    path('chart/', views.price_chart, name='price_chart'),
    path('open-trades/', views.open_trades, name='open_trades'),
    path('exit/<int:stock_id>/', views.exit_trade, name='exit_trade'),
]
