from django.urls import path

from . import views

app_name = 'paper_trading'

urlpatterns = [
    path('', views.paper_account, name='paper_account'),
    path('chart/', views.price_chart, name='price_chart'),
]
