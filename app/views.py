from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import Perfil, Materia, Atividade, Meta, Configuracao, RegistroEstudo
from .forms import (
    CustomAuthenticationForm, CadastroForm, PerfilForm,
    MateriaForm, AtividadeForm, MetaForm, ConfiguracaoForm
)
from .decorators import user_has_profile

def login_view(request):
    """Página de login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo de volta, {user.get_full_name() or user.username}!')
                return redirect('dashboard')
        else:
            messages.error(request, 'E-mail ou senha inválidos.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'core/login.html', {'form': form})


def cadastro_view(request):
    """Página de cadastro"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['email']
            user.email = form.cleaned_data['email']
            user.save()
            
            # Criar perfil
            perfil = Perfil.objects.create(
                usuario=user,
                objetivo=form.cleaned_data.get('objetivo', 'ENEM')
            )
            
            # Criar configurações padrão
            Configuracao.objects.create(usuario=user)
            
            messages.success(request, 'Conta criada com sucesso! Faça login para continuar.')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CadastroForm()
    
    return render(request, 'core/cadastro.html', {'form': form})


@login_required
def logout_view(request):
    """Logout do usuário"""
    logout(request)
    messages.info(request, 'Você saiu da sua conta.')
    return redirect('login')


@login_required
def dashboard(request):
    """Dashboard do usuário"""
    # Dados do usuário
    user = request.user
    perfil = Perfil.objects.get(usuario=user)
    
    # Estatísticas
    total_materias = Materia.objects.filter(usuario=user).count()
    total_atividades = Atividade.objects.filter(usuario=user).count()
    total_metas = Meta.objects.filter(usuario=user).count()
    
    # Atividades de hoje
    hoje = timezone.now().weekday()
    atividades_hoje = Atividade.objects.filter(
        usuario=user,
        dia_semana=hoje
    ).order_by('hora_inicio')
    
    # Metas em andamento
    metas_ativas = Meta.objects.filter(
        usuario=user
    ).exclude(status='completed').order_by('-progresso_atual')[:5]
    
    # Estatísticas de progresso
    progresso_medio = 0
    if total_materias > 0:
        progresso_medio = Materia.objects.filter(usuario=user).aggregate(
            Avg('progresso')
        )['progresso__avg'] or 0
        progresso_medio = round(progresso_medio)
    
    context = {
        'user': user,
        'perfil': perfil,
        'total_materias': total_materias,
        'total_atividades': total_atividades,
        'total_metas': total_metas,
        'atividades_hoje': atividades_hoje,
        'metas_ativas': metas_ativas,
        'progresso_medio': progresso_medio,
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def materias_view(request):
    """Página de matérias"""
    user = request.user
    
    if request.method == 'POST':
        form = MateriaForm(request.POST)
        if form.is_valid():
            materia = form.save(commit=False)
            materia.usuario = user
            materia.emoji = get_emoji_for_subject(form.cleaned_data['nome'])
            materia.save()
            messages.success(request, f'Matéria "{materia.nome}" criada com sucesso!')
            return redirect('materias')
        else:
            messages.error(request, 'Erro ao criar matéria. Verifique os dados.')
    else:
        form = MateriaForm()
    
    materias = Materia.objects.filter(usuario=user).order_by('-prioridade', 'nome')
    
    context = {
        'form': form,
        'materias': materias,
        'total_materias': materias.count(),
    }
    
    return render(request, 'core/materias.html', context)


@login_required
def materia_delete(request, pk):
    """Excluir matéria"""
    materia = get_object_or_404(Materia, pk=pk, usuario=request.user)
    nome = materia.nome
    materia.delete()
    messages.success(request, f'Matéria "{nome}" excluída com sucesso.')
    return redirect('materias')


@login_required
def materia_edit(request, pk):
    """Editar matéria (AJAX)"""
    materia = get_object_or_404(Materia, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        materia.nome = data.get('nome', materia.nome)
        materia.professor = data.get('professor', materia.professor)
        materia.topicos = data.get('topicos', materia.topicos)
        materia.carga_horaria = data.get('carga_horaria', materia.carga_horaria)
        materia.prioridade = data.get('prioridade', materia.prioridade)
        materia.progresso = data.get('progresso', materia.progresso)
        materia.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)


@login_required
def cronogramas_view(request):
    """Página de cronograma"""
    user = request.user
    
    if request.method == 'POST':
        form = AtividadeForm(request.POST)
        form.fields['materia'].queryset = Materia.objects.filter(usuario=user)
        if form.is_valid():
            atividade = form.save(commit=False)
            atividade.usuario = user
            atividade.save()
            messages.success(request, f'Atividade "{atividade.titulo}" criada com sucesso!')
            return redirect('cronogramas')
        else:
            messages.error(request, 'Erro ao criar atividade. Verifique os dados.')
    else:
        form = AtividadeForm()
        form.fields['materia'].queryset = Materia.objects.filter(usuario=user)
    
    atividades = Atividade.objects.filter(usuario=user).order_by('dia_semana', 'hora_inicio')
    
    # Agrupar atividades por dia
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    atividades_por_dia = {}
    for i, dia in enumerate(dias_semana):
        atividades_por_dia[dia] = atividades.filter(dia_semana=i)
    
    context = {
        'form': form,
        'atividades_por_dia': atividades_por_dia,
        'dias_semana': dias_semana,
        'total_atividades': atividades.count(),
    }
    
    return render(request, 'core/cronogramas.html', context)


@login_required
def atividade_delete(request, pk):
    """Excluir atividade"""
    atividade = get_object_or_404(Atividade, pk=pk, usuario=request.user)
    titulo = atividade.titulo
    atividade.delete()
    messages.success(request, f'Atividade "{titulo}" excluída com sucesso.')
    return redirect('cronogramas')


@login_required
def metas_view(request):
    """Página de metas"""
    user = request.user
    
    if request.method == 'POST':
        form = MetaForm(request.POST)
        form.fields['materia'].queryset = Materia.objects.filter(usuario=user)
        if form.is_valid():
            meta = form.save(commit=False)
            meta.usuario = user
            meta.status = meta.calcular_status()
            meta.save()
            messages.success(request, f'Meta "{meta.titulo}" criada com sucesso!')
            return redirect('metas')
        else:
            messages.error(request, 'Erro ao criar meta. Verifique os dados.')
    else:
        form = MetaForm()
        form.fields['materia'].queryset = Materia.objects.filter(usuario=user)
    
    metas = Meta.objects.filter(usuario=user).order_by('-data_criacao')
    
    # Contar por status
    total_metas = metas.count()
    metas_on_track = metas.filter(status='on-track').count()
    metas_at_risk = metas.filter(status='at-risk').count()
    metas_behind = metas.filter(status='behind').count()
    metas_completed = metas.filter(status='completed').count()
    
    context = {
        'form': form,
        'metas': metas,
        'total_metas': total_metas,
        'metas_on_track': metas_on_track,
        'metas_at_risk': metas_at_risk,
        'metas_behind': metas_behind,
        'metas_completed': metas_completed,
    }
    
    return render(request, 'core/metas.html', context)


@login_required
def meta_delete(request, pk):
    """Excluir meta"""
    meta = get_object_or_404(Meta, pk=pk, usuario=request.user)
    titulo = meta.titulo
    meta.delete()
    messages.success(request, f'Meta "{titulo}" excluída com sucesso.')
    return redirect('metas')


@login_required
def meta_update_status(request, pk):
    """Atualizar status da meta (AJAX)"""
    meta = get_object_or_404(Meta, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        meta.progresso_atual = data.get('progresso', meta.progresso_atual)
        meta.status = meta.calcular_status()
        meta.save()
        return JsonResponse({
            'success': True,
            'status': meta.get_status_display(),
            'status_class': meta.status,
            'progresso': meta.progresso_atual,
        })
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)


@login_required
def relatorios_view(request):
    """Página de relatórios"""
    user = request.user
    
    # Estatísticas gerais
    total_materias = Materia.objects.filter(usuario=user).count()
    total_atividades = Atividade.objects.filter(usuario=user).count()
    total_metas = Meta.objects.filter(usuario=user).count()
    
    # Progresso médio
    progresso_medio = 0
    if total_materias > 0:
        progresso_medio = Materia.objects.filter(usuario=user).aggregate(
            Avg('progresso')
        )['progresso__avg'] or 0
        progresso_medio = round(progresso_medio)
    
    # Atividades concluídas
    atividades_concluidas = Atividade.objects.filter(usuario=user, concluida=True).count()
    
    # Horas estudadas (simulação - em produção viria do RegistroEstudo)
    horas_estudadas = RegistroEstudo.objects.filter(usuario=user).aggregate(
        Sum('duracao_minutos')
    )['duracao_minutos__avg'] or 0
    horas_estudadas = round(horas_estudadas / 60, 1)
    
    # Ranking por matéria
    materias = Materia.objects.filter(usuario=user).order_by('-progresso')
    
    # Registros recentes
    registros_recentes = RegistroEstudo.objects.filter(usuario=user).order_by('-data', '-hora_inicio')[:10]
    
    context = {
        'total_materias': total_materias,
        'total_atividades': total_atividades,
        'total_metas': total_metas,
        'progresso_medio': progresso_medio,
        'atividades_concluidas': atividades_concluidas,
        'horas_estudadas': horas_estudadas,
        'materias': materias,
        'registros_recentes': registros_recentes,
    }
    
    return render(request, 'core/relatorios.html', context)


@login_required
def configuracoes_view(request):
    """Página de configurações"""
    user = request.user
    perfil = Perfil.objects.get(usuario=user)
    config, created = Configuracao.objects.get_or_create(usuario=user)
    
    if request.method == 'POST':
        perfil_form = PerfilForm(request.POST, instance=perfil)
        config_form = ConfiguracaoForm(request.POST, instance=config)
        
        if perfil_form.is_valid() and config_form.is_valid():
            perfil_form.save()
            config_form.save()
            
            # Atualizar nome do usuário
            nome = request.POST.get('nome_completo')
            if nome:
                user.first_name = nome
                user.save()
            
            messages.success(request, 'Configurações salvas com sucesso!')
            return redirect('configuracoes')
        else:
            messages.error(request, 'Erro ao salvar configurações.')
    else:
        perfil_form = PerfilForm(instance=perfil)
        config_form = ConfiguracaoForm(instance=config)
    
    context = {
        'perfil_form': perfil_form,
        'config_form': config_form,
        'perfil': perfil,
        'config': config,
    }
    
    return render(request, 'core/configuracoes.html', context)


@login_required
def config_salvar_tudo(request):
    """Salvar todas as configurações (AJAX)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        # Processar configurações
        messages.success(request, 'Todas as configurações foram salvas com sucesso!')
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)


# ===== FUNÇÕES AUXILIARES =====

def get_emoji_for_subject(nome):
    """Retorna emoji para uma matéria"""
    emojis = {
        'matemática': '📐',
        'matematica': '📐',
        'biologia': '🧬',
        'história': '📜',
        'historia': '📜',
        'português': '📝',
        'portugues': '📝',
        'física': '⚡',
        'fisica': '⚡',
        'química': '🧪',
        'quimica': '🧪',
        'geografia': '🌍',
        'inglês': '🇬🇧',
        'ingles': '🇬🇧',
        'espanhol': '🇪🇸',
        'filosofia': '🧠',
        'sociologia': '👥',
        'artes': '🎨',
    }
    
    nome_lower = nome.lower()
    for key, emoji in emojis.items():
        if key in nome_lower:
            return emoji
    return '📖'


def get_prioridade_color(prioridade):
    """Retorna cor para prioridade"""
    cores = {
        'high': 'linear-gradient(135deg, #dc2626, #ef4444)',
        'medium': 'linear-gradient(135deg, #ca8a04, #eab308)',
        'low': 'linear-gradient(135deg, #16a34a, #22c55e)',
    }
    return cores.get(prioridade, 'linear-gradient(135deg, #64748b, #94a3b8)')


def get_prioridade_label(prioridade):
    """Retorna label para prioridade"""
    labels = {
        'high': 'Alta',
        'medium': 'Média',
        'low': 'Baixa',
    }
    return labels.get(prioridade, 'Média')