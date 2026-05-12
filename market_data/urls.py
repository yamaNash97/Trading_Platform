from django.urls import path

from . import views

app_name = 'market_data'

urlpatterns = [
    path('', views.stock_list, name='stock_list'),
    path('commodities/import/', views.import_commodities, name='import_commodities'),
    path('chart/', views.stock_chart, name='stock_chart'),
    path('<int:pk>/', views.stock_detail, name='stock_detail'),
    path('<int:pk>/chart/', views.stock_price_chart, name='stock_price_chart'),
    path('<int:pk>/seed/', views.seed_prices, name='seed_prices'),
    path('<int:pk>/refresh/', views.refresh_alpha_vantage, name='refresh_alpha_vantage'),
]
