from django import forms

from .models import Order


class OrderForm(forms.ModelForm):
    """Collect the user-editable fields for a paper-trading order.

    The user chooses a stock, side, and quantity. Price, status, user, and
    filled time are set by the service, so posted form data cannot skip balance
    or holdings checks.
    """

    class Meta:
        model = Order
        fields = ('stock', 'order_type', 'quantity')
        widgets = {
            # The UI accepts fractional amounts while the service checks cash
            # and available holdings.
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.000001', 'step': '0.000001'}),
        }

    def __init__(self, *args, **kwargs):
        """Apply Bootstrap classes to generated select widgets."""
        super().__init__(*args, **kwargs)
        self.fields['stock'].widget.attrs.setdefault('class', 'form-select')
        self.fields['order_type'].widget.attrs.setdefault('class', 'form-select')
