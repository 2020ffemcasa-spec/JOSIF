from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import Perfil, Materia, Atividade, Meta, Configuracao, RegistroEstudo
from .forms import (
    CustomAuthenticationForm, CadastroForm, PerfilForm,
    MateriaForm, AtividadeForm, MetaForm, ConfiguracaoForm
)

def login_view(request):
    """Página de login"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo de volta, {user.get_full_name() or user.username}!')
                return redirect('core:dashboard')
        else:
            messages.error(request, 'E-mail ou senha inválidos.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'core/login.html', {'form': form})


def cadastro_view(request):
    """Página de cadastro"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['email']
            user.email = form.cleaned_data['email']
            user.save()
            
            # Criar perfil
            Perfil.objects.create(
                usuario=user,
                objetivo=form.cleaned_data.get('objetivo', 'ENEM')
            )
            
            # Criar configurações padrão
            Configuracao.objects.create(usuario=user)
            
            messages.success(request, 'Conta criada com sucesso! Faça login para continuar.')
            return redirect('core:login')
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
    return redirect('core:login')


@login_required
def dashboard(request):
    """Dashboard do usuário"""
    user = request.user
    
    # Estatísticas
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
    
    context = {
        'user': user,
        'total_materias': total_materias,
        'total_atividades': total_atividades,
        'total_metas': total_metas,
        'progresso_medio': progresso_medio,
        'atividades_hoje': atividades_hoje,
        'metas_ativas': metas_ativas,
    }
    
    return render(request, 'core/dashboard.html', context)
@login_required
def upload_avatar(request):
    """Upload da foto de perfil"""
    if request.method == 'POST' and request.FILES.get('avatar'):
        perfil, created = Perfil.objects.get_or_create(usuario=request.user)
        perfil.avatar = request.FILES['avatar']
        perfil.save()
        return JsonResponse({
            'success': True,
            'message': 'Foto atualizada com sucesso!',
            'url': perfil.avatar.url
        })
    return JsonResponse({'success': False, 'message': 'Nenhuma imagem enviada'}, status=400)

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
            return redirect('core:materias')
        else:
            messages.error(request, 'Erro ao criar matéria. Verifique os dados.')
    else:
        form = MateriaForm()
    
    materias = Materia.objects.filter(usuario=user).order_by('-prioridade', 'nome')
    
    context = {
        'form': form,
        'materias': materias,
    }
    
    return render(request, 'core/materias.html', context)


@login_required
def materia_delete(request, pk):
    """Excluir matéria"""
    materia = get_object_or_404(Materia, pk=pk, usuario=request.user)
    nome = materia.nome
    materia.delete()
    messages.success(request, f'Matéria "{nome}" excluída com sucesso.')
    return redirect('core:materias')


@login_required
def materia_edit(request, pk):
    """Editar matéria (GET para buscar dados, POST para salvar)"""
    materia = get_object_or_404(Materia, pk=pk, usuario=request.user)
    
    if request.method == 'GET':
        return JsonResponse({
            'id': materia.id,
            'nome': materia.nome,
            'professor': materia.professor or '',
            'topicos': materia.topicos or '',
            'carga_horaria': materia.carga_horaria,
            'prioridade': materia.prioridade,
            'progresso': materia.progresso,
        })
    
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
            return redirect('core:cronogramas')
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
        'materias': Materia.objects.filter(usuario=user).order_by('nome'),
        'hoje': timezone.now().weekday(),
        'total_atividades': atividades.count(),
        'total_materias': Materia.objects.filter(usuario=user).count(),
    }
    
    return render(request, 'core/cronogramas.html', context)


@login_required
def atividade_delete(request, pk):
    """Excluir atividade"""
    atividade = get_object_or_404(Atividade, pk=pk, usuario=request.user)
    titulo = atividade.titulo
    atividade.delete()
    messages.success(request, f'Atividade "{titulo}" excluída com sucesso.')
    return redirect('core:cronogramas')


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
            return redirect('core:metas')
        else:
            messages.error(request, 'Erro ao criar meta. Verifique os dados.')
    else:
        form = MetaForm()
        form.fields['materia'].queryset = Materia.objects.filter(usuario=user)
    
    metas = Meta.objects.filter(usuario=user).order_by('-data_criacao')
    
    context = {
        'form': form,
        'metas': metas,
        'materias': Materia.objects.filter(usuario=user).order_by('nome'),
    }
    
    return render(request, 'core/metas.html', context)


@login_required
def meta_delete(request, pk):
    """Excluir meta"""
    meta = get_object_or_404(Meta, pk=pk, usuario=request.user)
    titulo = meta.titulo
    meta.delete()
    messages.success(request, f'Meta "{titulo}" excluída com sucesso.')
    return redirect('core:metas')


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
    
    # ===== HORAS ESTUDADAS (CORRIGIDO) =====
    # Buscar todos os registros de estudo do usuário
    registros = RegistroEstudo.objects.filter(usuario=user)
    
    # Calcular total de minutos
    total_minutos = 0
    for registro in registros:
        total_minutos += registro.duracao_minutos
    
    # Converter para horas (1 casa decimal)
    horas_estudadas = round(total_minutos / 60, 1)
    
    # Se não tiver registros, mostrar 0
    if horas_estudadas == 0:
        horas_estudadas = 0.0
    
    # Ranking por matéria
    materias = Materia.objects.filter(usuario=user).order_by('-progresso')
    
    # Registros recentes
    registros_recentes = RegistroEstudo.objects.filter(usuario=user).order_by('-data', '-hora_inicio')[:10]
    
    # Dados para o gráfico (últimos 7 dias)
    hoje = timezone.now().date()
    dias_semana = []
    horas_por_dia = []
    
    for i in range(6, -1, -1):
        dia = hoje - timedelta(days=i)
        # Nome do dia em português
        dias_pt = {
            'Mon': 'Seg', 'Tue': 'Ter', 'Wed': 'Qua',
            'Thu': 'Qui', 'Fri': 'Sex', 'Sat': 'Sáb', 'Sun': 'Dom'
        }
        dia_nome = dia.strftime('%a')
        dias_semana.append(dias_pt.get(dia_nome, dia_nome))
        
        # Buscar horas estudadas neste dia
        registros_dia = RegistroEstudo.objects.filter(
            usuario=user,
            data=dia
        )
        total_minutos_dia = 0
        for reg in registros_dia:
            total_minutos_dia += reg.duracao_minutos
        horas_por_dia.append(round(total_minutos_dia / 60, 1))
    
    context = {
        'total_materias': total_materias,
        'total_atividades': total_atividades,
        'total_metas': total_metas,
        'progresso_medio': progresso_medio,
        'atividades_concluidas': atividades_concluidas,
        'horas_estudadas': horas_estudadas,
        'materias': materias,
        'registros_recentes': registros_recentes,
        'dias_semana': dias_semana,
        'horas_por_dia': horas_por_dia,
    }
    
    return render(request, 'core/relatorios.html', context)

@login_required
def configuracoes_view(request):
    """Página de configurações"""
    user = request.user
    perfil, created = Perfil.objects.get_or_create(usuario=user)
    config, created = Configuracao.objects.get_or_create(usuario=user)
    
    if request.method == 'POST':
        # Verifica se é JSON ou formulário
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Salvar perfil
        if 'nome' in data:
            user.first_name = data['nome']
            user.save()
        
        if 'email' in data:
            user.email = data['email']
            user.save()
        
        if 'telefone' in data:
            perfil.telefone = data['telefone']
        
        if 'data_nascimento' in data and data['data_nascimento']:
            perfil.data_nascimento = datetime.strptime(data['data_nascimento'], '%Y-%m-%d').date()
        
        if 'instituicao' in data:
            perfil.instituicao = data['instituicao']
        
        if 'serie' in data:
            perfil.serie = data['serie']
        
        if 'objetivo' in data:
            perfil.objetivo = data['objetivo']
        
        perfil.save()
        
        # Salvar configurações
        if 'tema' in data:
            config.tema = data['tema']
        
        if 'cor_primaria' in data:
            config.cor_primaria = data['cor_primaria']
        
        config.save()
        
        if request.content_type == 'application/json':
            return JsonResponse({'success': True, 'message': 'Configurações salvas com sucesso!'})
        else:
            messages.success(request, 'Configurações salvas com sucesso!')
            return redirect('core:configuracoes')
    
    # GET - Carregar dados
    context = {
        'perfil': perfil,
        'config': config,
        'user': user,
    }
    
    return render(request, 'core/configuracoes.html', context)

@login_required
def config_salvar_tudo(request):
    """Salvar todas as configurações (AJAX)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        
        config, created = Configuracao.objects.get_or_create(usuario=request.user)
        
        if 'tema' in data:
            config.tema = data['tema']
        if 'cor_primaria' in data:
            config.cor_primaria = data['cor_primaria']
        if 'notificacoes_email' in data:
            config.notificacoes_email = data['notificacoes_email'] == 'true'
        if 'lembrete_diario' in data:
            config.lembrete_diario = data['lembrete_diario'] == 'true'
        
        config.save()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)

# ===== FUNÇÕES AUXILIARES =====
@login_required
def meta_edit(request, pk):
    """Editar meta (GET para buscar dados, POST para salvar)"""
    meta = get_object_or_404(Meta, pk=pk, usuario=request.user)
    
    if request.method == 'GET':
        return JsonResponse({
            'id': meta.id,
            'titulo': meta.titulo,
            'materia': meta.materia_id if meta.materia else '',
            'descricao': meta.descricao or '',
            'meta_progresso': meta.meta_progresso,
            'progresso_atual': meta.progresso_atual,
            'prazo': meta.prazo.strftime('%Y-%m-%d') if meta.prazo else '',
            'status': meta.status,
        })
    
    elif request.method == 'POST':
        # Verifica se é JSON ou formulário
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            # É um formulário normal (POST)
            data = request.POST
        
        meta.titulo = data.get('titulo', meta.titulo)
        meta.descricao = data.get('descricao', meta.descricao)
        meta.meta_progresso = int(data.get('meta_progresso', meta.meta_progresso))
        meta.progresso_atual = int(data.get('progresso_atual', meta.progresso_atual))
        meta.prazo = data.get('prazo') if data.get('prazo') else None
        meta.materia_id = data.get('materia') if data.get('materia') else None
        meta.status = meta.calcular_status()
        meta.save()
        
        messages.success(request, f'Meta "{meta.titulo}" atualizada com sucesso!')
        return redirect('core:metas')
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)


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