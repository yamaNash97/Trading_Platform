import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backtesting', '0002_widen_backtest_percentage_fields'),
        ('strategies', '0002_alter_strategy_stock'),
    ]

    operations = [
        migrations.AlterField(
            model_name='backtestresult',
            name='strategy',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='backtests', to='strategies.strategy'),
        ),
    ]
