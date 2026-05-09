from django import forms

from .models import Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('stock', 'order_type', 'quantity')
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.000001', 'step': '0.000001'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['stock'].widget.attrs.setdefault('class', 'form-select')
        self.fields['order_type'].widget.attrs.setdefault('class', 'form-select')
