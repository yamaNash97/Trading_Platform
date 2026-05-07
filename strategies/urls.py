from django.urls import path

from . import views

app_name = 'strategies'

urlpatterns = [
    path('', views.strategy_list, name='strategy_list'),
    path('new/', views.strategy_create, name='strategy_create'),
    path('<int:pk>/', views.strategy_detail, name='strategy_detail'),
]
