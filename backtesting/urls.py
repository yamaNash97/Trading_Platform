from django.urls import path

from . import views

app_name = 'backtesting'

urlpatterns = [
    path('', views.backtest_list, name='backtest_list'),
    path('<int:pk>/', views.backtest_detail, name='backtest_detail'),
]
