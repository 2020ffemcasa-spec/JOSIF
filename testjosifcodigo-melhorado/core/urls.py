from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Autenticação
    path('', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Matérias
    path('materias/', views.materias_view, name='materias'),
    path('materias/delete/<int:pk>/', views.materia_delete, name='materia_delete'),
    path('materias/edit/<int:pk>/', views.materia_edit, name='materia_edit'),
    
    # Cronograma
    path('cronogramas/', views.cronogramas_view, name='cronogramas'),
    path('cronogramas/toggle/<int:pk>/', views.atividade_toggle, name='atividade_toggle'),
    path('cronogramas/delete/<int:pk>/', views.atividade_delete, name='atividade_delete'),
    
    # Metas
    path('metas/', views.metas_view, name='metas'),
    path('metas/delete/<int:pk>/', views.meta_delete, name='meta_delete'),
    path('metas/edit/<int:pk>/', views.meta_edit, name='meta_edit'),
    
    # Relatórios
    path('relatorios/', views.relatorios_view, name='relatorios'),
    
    # Configurações
    path('configuracoes/salvar/', views.config_salvar_tudo, name='config_salvar_tudo'),
    path('configuracoes/exportar/', views.exportar_dados, name='exportar_dados'),
    path('configuracoes/feedback/', views.enviar_feedback, name='enviar_feedback'),
    path('configuracoes/senha/', views.alterar_senha, name='alterar_senha'),
    path('configuracoes/excluir/', views.excluir_conta, name='excluir_conta'),
    path('configuracoes/', views.configuracoes_view, name='configuracoes'),
    path('upload-avatar/', views.upload_avatar, name='upload_avatar'),
]