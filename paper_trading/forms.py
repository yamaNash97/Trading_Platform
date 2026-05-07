from django import forms

from .models import Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('stock', 'order_type', 'quantity')
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': '0.000001', 'step': '0.000001'}),
        }
