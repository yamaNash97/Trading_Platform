from django.urls import path

from . import views

app_name = 'accounts'

# App-owned auth URL for registration; login/logout/password URLs come from
# django.contrib.auth.urls in config.urls.
urlpatterns = [
    path('signup/', views.signup, name='signup'),
]
