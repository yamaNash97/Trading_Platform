from django.urls import path

from . import views

app_name = 'portfolio'

# Public visitors land on the home page; logged-in users go to the dashboard
# after login through LOGIN_REDIRECT_URL in settings.py.
urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
