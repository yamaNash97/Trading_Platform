from django import forms

from .models import Stock


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ('symbol', 'name', 'exchange', 'currency')
        widgets = {
            'symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AAPL'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apple Inc.'}),
            'exchange': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NASDAQ'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
        }
