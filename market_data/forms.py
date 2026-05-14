from django import forms

from .models import Stock


class StockForm(forms.ModelForm):
    """Create or edit the small set of Stock fields shown to users.

    Users enter the symbol, name, exchange, and currency. Price rows are added
    later by sample seeding or import services.
    """

    class Meta:
        model = Stock
        fields = ('symbol', 'name', 'exchange', 'currency')
        # Bootstrap classes are set here so templates can use form.as_p without
        # repeating widget HTML.
        widgets = {
            'symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AAPL'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apple Inc.'}),
            'exchange': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NASDAQ'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
        }
