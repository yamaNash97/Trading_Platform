from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
