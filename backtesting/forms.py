from django import forms

from strategies.models import Strategy


class BacktestRunForm(forms.Form):
    strategy = forms.ModelChoiceField(queryset=Strategy.objects.none())
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['strategy'].queryset = Strategy.objects.filter(user=user, is_active=True).select_related('stock')

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')
        if start_date and end_date and start_date >= end_date:
            self.add_error('end_date', 'End date must be after start date.')
        return cleaned
