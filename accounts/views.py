from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import SignUpForm


def signup(request):
    if request.user.is_authenticated:
        logout(request)
        return redirect('accounts:signup')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('portfolio:dashboard')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})
