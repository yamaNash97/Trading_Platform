import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_data', '0001_initial'),
        ('strategies', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='strategy',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='strategies', to='market_data.stock'),
        ),
    ]
