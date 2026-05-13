from django.urls import path

from . import views

app_name = 'portfolio'

# Public visitors land on the marketing page; authenticated users are sent to
# the dashboard after login by LOGIN_REDIRECT_URL in settings.py.
urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
