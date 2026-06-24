from django.contrib import admin
from .models import Perfil, Materia, Atividade, Meta, Configuracao, RegistroEstudo


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'get_nome', 'objetivo', 'data_cadastro']
    search_fields = ['usuario__username', 'usuario__email', 'usuario__first_name']
    list_filter = ['objetivo', 'serie']
    
    def get_nome(self, obj):
        return obj.usuario.get_full_name() or obj.usuario.username
    get_nome.short_description = 'Nome'


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'usuario', 'prioridade', 'progresso', 'carga_horaria']
    search_fields = ['nome', 'professor', 'usuario__username']
    list_filter = ['prioridade', 'usuario']


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'usuario', 'materia', 'dia_semana', 'hora_inicio', 'hora_fim', 'concluida']
    search_fields = ['titulo', 'usuario__username', 'materia__nome']
    list_filter = ['dia_semana', 'concluida', 'usuario']


@admin.register(Meta)
class MetaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'usuario', 'materia', 'progresso_atual', 'meta_progresso', 'status', 'prazo']
    search_fields = ['titulo', 'usuario__username', 'materia__nome']
    list_filter = ['status', 'usuario']


@admin.register(Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tema', 'notificacoes_email', 'lembrete_diario']
    search_fields = ['usuario__username', 'usuario__email']


@admin.register(RegistroEstudo)
class RegistroEstudoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'materia', 'data', 'duracao_minutos']
    search_fields = ['usuario__username', 'materia__nome']
    list_filter = ['data', 'usuario']