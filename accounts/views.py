from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import SignUpForm


def signup(request):
    """Register a new user and sign them in immediately.

    Authenticated visitors are logged out first so the signup page always
    creates a fresh account rather than mutating the current session.
    """
    if request.user.is_authenticated:
        logout(request)
        return redirect('accounts:signup')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the new user in so the normal post-login dashboard redirect
            # happens without asking them to authenticate again.
            login(request, user)
            return redirect('portfolio:dashboard')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})
