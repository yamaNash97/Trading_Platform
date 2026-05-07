from django import forms

from .models import Stock


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ('symbol', 'name', 'exchange', 'currency')
        widgets = {
            'symbol': forms.TextInput(attrs={'placeholder': 'AAPL'}),
            'name': forms.TextInput(attrs={'placeholder': 'Apple Inc.'}),
            'exchange': forms.TextInput(attrs={'placeholder': 'NASDAQ'}),
        }
