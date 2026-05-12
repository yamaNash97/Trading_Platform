from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backtesting', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='backtestresult',
            name='max_drawdown',
            field=models.DecimalField(decimal_places=2, max_digits=12),
        ),
        migrations.AlterField(
            model_name='backtestresult',
            name='total_return',
            field=models.DecimalField(decimal_places=2, max_digits=12),
        ),
        migrations.AlterField(
            model_name='backtestresult',
            name='win_loss_ratio',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
