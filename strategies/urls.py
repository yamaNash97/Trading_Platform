from django.urls import path

from . import views

app_name = 'strategies'

# Strategy URLs cover the list page, the creation form, and read-only detail.
urlpatterns = [
    path('', views.strategy_list, name='strategy_list'),
    path('new/', views.strategy_create, name='strategy_create'),
    path('<int:pk>/', views.strategy_detail, name='strategy_detail'),
]
