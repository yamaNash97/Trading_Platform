from django import forms

from .models import Strategy


class StrategyForm(forms.ModelForm):
    short_window = forms.IntegerField(min_value=2, initial=20)
    long_window = forms.IntegerField(min_value=3, initial=50)
    rsi_period = forms.IntegerField(min_value=2, initial=14)
    rsi_buy_threshold = forms.IntegerField(min_value=1, max_value=99, initial=30)
    rsi_sell_threshold = forms.IntegerField(min_value=1, max_value=99, initial=70)

    class Meta:
        model = Strategy
        fields = (
            'stock',
            'name',
            'strategy_type',
            'initial_balance',
            'position_size_percent',
            'stop_loss_percent',
            'take_profit_percent',
            'is_active',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_active':
                field.widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')
        if self.instance and self.instance.pk:
            params = self.instance.parameters or {}
            for field in ('short_window', 'long_window', 'rsi_period', 'rsi_buy_threshold', 'rsi_sell_threshold'):
                self.fields[field].initial = params.get(field, self.fields[field].initial)

    def clean(self):
        cleaned = super().clean()
        short_window = cleaned.get('short_window')
        long_window = cleaned.get('long_window')
        if short_window and long_window and short_window >= long_window:
            self.add_error('long_window', 'Long moving average must be greater than short moving average.')
        return cleaned

    def save(self, commit=True):
        strategy = super().save(commit=False)
        strategy.parameters = {
            'short_window': self.cleaned_data['short_window'],
            'long_window': self.cleaned_data['long_window'],
            'rsi_period': self.cleaned_data['rsi_period'],
            'rsi_buy_threshold': self.cleaned_data['rsi_buy_threshold'],
            'rsi_sell_threshold': self.cleaned_data['rsi_sell_threshold'],
        }
        if commit:
            strategy.save()
            self.save_m2m()
        return strategy
