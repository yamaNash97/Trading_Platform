from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paper_trading', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='quantity',
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='quantity',
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
    ]
