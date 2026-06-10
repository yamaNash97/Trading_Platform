from decimal import Decimal

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from .models import Strategy


class StrategyForm(forms.ModelForm):
    """Collect strategy details, risk settings, and indicator fields.

    Model fields store the common settings, while the extra indicator
    fields are packed into ``Strategy.parameters`` during ``save``.
    """

    # Indicator fields are not model columns; they are saved inside the
    # strategy JSON settings so users still see clear fields.
    INDICATOR_DEFAULTS = {
        'short_window': 20,
        'long_window': 50,
        'rsi_period': 14,
        'rsi_buy_threshold': 30,
        'rsi_sell_threshold': 70,
    }
    MA_FIELDS = ('short_window', 'long_window')
    RSI_FIELDS = ('rsi_period', 'rsi_buy_threshold', 'rsi_sell_threshold')

    short_window = forms.IntegerField(min_value=2, initial=INDICATOR_DEFAULTS['short_window'], required=False)
    long_window = forms.IntegerField(min_value=3, initial=INDICATOR_DEFAULTS['long_window'], required=False)
    rsi_period = forms.IntegerField(min_value=2, initial=INDICATOR_DEFAULTS['rsi_period'], required=False)
    rsi_buy_threshold = forms.IntegerField(
        min_value=1,
        max_value=99,
        initial=INDICATOR_DEFAULTS['rsi_buy_threshold'],
        required=False,
    )
    rsi_sell_threshold = forms.IntegerField(
        min_value=1,
        max_value=99,
        initial=INDICATOR_DEFAULTS['rsi_sell_threshold'],
        required=False,
    )
    initial_balance = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1'))],
    )
    position_size_percent = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.01')),
            MaxValueValidator(Decimal('100')),
        ],
    )
    stop_loss_percent = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    take_profit_percent = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )

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
        """Apply Bootstrap widgets and load JSON-backed initial values."""
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'is_active':
                field.widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            else:
                field.widget.attrs.setdefault('class', 'form-control')
        if self.instance and self.instance.pk:
            # Existing strategies keep their indicator settings in parameters.
            params = self.instance.parameters or {}
            for field in ('short_window', 'long_window', 'rsi_period', 'rsi_buy_threshold', 'rsi_sell_threshold'):
                self.fields[field].initial = params.get(field, self.fields[field].initial)

    def clean(self):
        """Validate money, risk percentage, and indicator relationships."""
        cleaned = super().clean()
        initial_balance = cleaned.get('initial_balance')
        position_size_percent = cleaned.get('position_size_percent')
        stop_loss_percent = cleaned.get('stop_loss_percent')
        take_profit_percent = cleaned.get('take_profit_percent')
        strategy_type = cleaned.get('strategy_type')
        active_indicator_fields = ()
        if strategy_type == Strategy.StrategyType.MOVING_AVERAGE:
            active_indicator_fields = self.MA_FIELDS
        elif strategy_type == Strategy.StrategyType.RSI:
            active_indicator_fields = self.RSI_FIELDS
        elif strategy_type == Strategy.StrategyType.COMBINED:
            active_indicator_fields = self.MA_FIELDS + self.RSI_FIELDS

        for field_name, default in self.INDICATOR_DEFAULTS.items():
            if field_name in active_indicator_fields and cleaned.get(field_name) is None:
                self.add_error(field_name, 'This field is required for the selected strategy type.')
            elif cleaned.get(field_name) is None:
                cleaned[field_name] = default

        if initial_balance is not None and initial_balance <= Decimal('0'):
            self.add_error('initial_balance', 'Initial balance must be positive.')
        if position_size_percent is not None and (
            position_size_percent <= Decimal('0') or position_size_percent > Decimal('100')
        ):
            self.add_error('position_size_percent', 'Position size must be greater than 0 and no more than 100%.')
        if stop_loss_percent is not None and stop_loss_percent < Decimal('0'):
            self.add_error('stop_loss_percent', 'Stop loss must be 0 or greater.')
        if take_profit_percent is not None and take_profit_percent < Decimal('0'):
            self.add_error('take_profit_percent', 'Take profit must be 0 or greater.')
        short_window = cleaned.get('short_window')
        long_window = cleaned.get('long_window')
        if strategy_type in (Strategy.StrategyType.MOVING_AVERAGE, Strategy.StrategyType.COMBINED) and (
            short_window is not None
            and long_window is not None
            and short_window >= long_window
        ):
            self.add_error('long_window', 'Long moving average must be greater than short moving average.')
        return cleaned

    def save(self, commit=True):
        """Save JSON-backed indicator fields with the model fields."""
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
