import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    """RegistroEstudo.data deixa de ser auto_now_add para aceitar a data escolhida pelo usuário."""

    dependencies = [
        ('core', '0002_alter_registroestudo_materia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registroestudo',
            name='data',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='Data'),
        ),
    ]
