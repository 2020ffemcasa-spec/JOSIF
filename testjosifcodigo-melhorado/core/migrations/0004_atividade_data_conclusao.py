from django.db import migrations, models


def preencher_data_conclusao(apps, schema_editor):
    """Atividades já concluídas ganham uma data (a da criação) para entrarem nos relatórios."""
    Atividade = apps.get_model('core', 'Atividade')
    for atividade in Atividade.objects.filter(concluida=True, data_conclusao__isnull=True):
        atividade.data_conclusao = atividade.data_criacao.date()
        atividade.save(update_fields=['data_conclusao'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_registroestudo_data_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='atividade',
            name='data_conclusao',
            field=models.DateField(blank=True, null=True, verbose_name='Data de Conclusao'),
        ),
        migrations.RunPython(preencher_data_conclusao, migrations.RunPython.noop),
    ]
