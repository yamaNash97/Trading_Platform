from django.urls import path

from . import views

app_name = 'accounts'

# This app owns signup; login/logout/password URLs come from Django auth URLs
# in config.urls.
urlpatterns = [
    path('signup/', views.signup, name='signup'),
]
