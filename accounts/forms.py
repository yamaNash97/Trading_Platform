from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    """User registration form shown on the signup page.

    It extends Django's built-in password validation flow and exposes only the
    username/email fields from ``User`` plus the inherited password fields.
    """

    class Meta:
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        """Apply Bootstrap styling to all generated form controls."""
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
