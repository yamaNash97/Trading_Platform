from django import forms

from .models import Stock


class StockForm(forms.ModelForm):
    """Create or edit the small set of Stock fields exposed to users.

    The form keeps instrument setup intentionally simple: users provide the
    market identifier and optional exchange/currency metadata, while price rows
    are created separately by sample seeding or import services.
    """

    class Meta:
        model = Stock
        fields = ('symbol', 'name', 'exchange', 'currency')
        # Bootstrap classes are assigned here so templates can render the form
        # with form.as_p without duplicating widget markup.
        widgets = {
            'symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AAPL'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apple Inc.'}),
            'exchange': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NASDAQ'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
        }
