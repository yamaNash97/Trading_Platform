from django import forms

from strategies.models import Strategy


class BacktestRunForm(forms.Form):
    """Collect the strategy and date range for a backtest run."""

    # The queryset is filled per user in __init__ so users only backtest their
    # own active strategies.
    strategy = forms.ModelChoiceField(queryset=Strategy.objects.none(), widget=forms.Select(attrs={'class': 'form-select'}))
    start_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))

    def __init__(self, *args, user=None, **kwargs):
        """Limit strategy choices to the signed-in user's active strategies."""
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['strategy'].queryset = Strategy.objects.filter(user=user, is_active=True).select_related('stock')

    def clean(self):
        """Validate that the selected date range moves forward in time."""
        cleaned = super().clean()
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')
        if start_date and end_date and start_date >= end_date:
            self.add_error('end_date', 'End date must be after start date.')
        return cleaned
