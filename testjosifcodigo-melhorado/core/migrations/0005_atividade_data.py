from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


def preencher_data(apps, schema_editor):
    """Atividades existentes ficam na semana em que foram criadas (no dia da semana escolhido)."""
    Atividade = apps.get_model('core', 'Atividade')
    for atividade in Atividade.objects.filter(data__isnull=True):
        criada = timezone.localtime(atividade.data_criacao).date()
        segunda = criada - timedelta(days=criada.weekday())
        atividade.data = segunda + timedelta(days=atividade.dia_semana)
        atividade.save(update_fields=['data'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_atividade_data_conclusao'),
    ]

    operations = [
        migrations.AddField(
            model_name='atividade',
            name='data',
            field=models.DateField(blank=True, null=True, verbose_name='Data'),
        ),
        migrations.RunPython(preencher_data, migrations.RunPython.noop),
    ]
