import json
import re
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    AtividadeForm, CadastroForm, CustomAuthenticationForm,
    MateriaForm, MetaForm,
)
from .models import Atividade, Configuracao, Feedback, Materia, Meta, Perfil

MESES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
DIAS_ABREV = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

NIVEIS = [
    (0, 'Iniciante'),
    (50, 'Estudante'),
    (150, 'Determinado'),
    (300, 'Disciplinado'),
    (500, 'Mestre dos Estudos'),
]

TEMAS_VALIDOS = {'light', 'dark', 'blue'}
PALETA = ['#0891b2', '#16a34a', '#2878FF', '#334155', '#7c3aed', '#d97706', '#e11d48', '#ea580c']
AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
AVATAR_FORMATOS = {'JPEG', 'PNG', 'WEBP', 'GIF'}


# ===================== FUNÇÕES AUXILIARES =====================

def calcular_nivel(pontos):
    """Retorna nome do nível, próximo limiar e progresso até ele."""
    nivel = NIVEIS[0][1]
    proximo = None
    for limiar, nome in NIVEIS:
        if pontos >= limiar:
            nivel = nome
        elif proximo is None:
            proximo = limiar
    if proximo is None:
        return nivel, None, 100
    base = max([limiar for limiar, _ in NIVEIS if limiar < proximo])
    progresso = min(100, int((pontos - base) / (proximo - base) * 100))
    return nivel, proximo, progresso


def ler_json(request):
    """Lê o corpo JSON da requisição. Retorna None se for inválido (em vez de gerar erro 500)."""
    try:
        dados = json.loads(request.body or b'{}')
    except (ValueError, UnicodeDecodeError):
        return None
    return dados if isinstance(dados, dict) else None


def eh_json(request):
    return (request.content_type or '').startswith('application/json')


def erros_do_form(form):
    """Transforma os erros de um form em mensagens legíveis ('Rótulo: erro')."""
    mensagens = []
    for campo, erros in form.errors.items():
        rotulo = form.fields[campo].label if campo in form.fields and form.fields[campo].label else None
        for erro in erros:
            mensagens.append(f'{rotulo}: {erro}' if rotulo else str(erro))
    return mensagens


def destino_seguro(request, padrao):
    """Usa o parâmetro `next` apenas se apontar para este mesmo site (evita open redirect)."""
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return padrao


def atualizar_status_metas(usuario):
    """Recalcula o status das metas abertas (ex.: prazo vencido desde a última visita)."""
    for meta in Meta.objects.filter(usuario=usuario).exclude(status='completed'):
        novo = meta.calcular_status()
        if novo != meta.status:
            meta.status = novo
            meta.save(update_fields=['status'])


def normalizar_cor(valor):
    """Aceita '#rrggbb' ou 'rgb(r, g, b)' (o que o navegador devolve em style.background)."""
    valor = (valor or '').strip()
    hex_cor = None
    if re.fullmatch(r'#[0-9a-fA-F]{6}', valor):
        hex_cor = valor.lower()
    else:
        m = re.fullmatch(r'rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)', valor)
        if m and all(int(c) <= 255 for c in m.groups()):
            hex_cor = '#%02x%02x%02x' % tuple(int(c) for c in m.groups())
    if not hex_cor:
        return None
    # Devolve a grafia usada pela paleta (o template compara texto exato)
    for cor in PALETA:
        if cor.lower() == hex_cor:
            return cor
    return hex_cor


def get_emoji_for_subject(nome):
    """Retorna emoji para uma matéria"""
    emojis = {
        'matemática': '📐', 'matematica': '📐',
        'biologia': '🧬',
        'história': '📜', 'historia': '📜',
        'português': '📝', 'portugues': '📝',
        'física': '⚡', 'fisica': '⚡',
        'química': '🧪', 'quimica': '🧪',
        'geografia': '🌍',
        'inglês': '🇬🇧', 'ingles': '🇬🇧',
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


# ===================== AUTENTICAÇÃO =====================

def login_view(request):
    """Página de login"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # O AuthenticationForm já autenticou o usuário em is_valid()
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bem-vindo de volta, {user.get_full_name() or user.username}!')
            return redirect(destino_seguro(request, 'core:dashboard'))
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
            # Cria usuário, perfil e configurações juntos: ou tudo ou nada
            with transaction.atomic():
                user = form.save(commit=False)
                user.username = form.cleaned_data['email']
                user.email = form.cleaned_data['email']
                user.save()
                Perfil.objects.create(
                    usuario=user,
                    objetivo=form.cleaned_data.get('objetivo') or 'ENEM',
                )
                Configuracao.objects.create(usuario=user)

            messages.success(request, 'Conta criada com sucesso! Faça login para continuar.')
            return redirect('core:login')
        for mensagem in erros_do_form(form):
            messages.error(request, mensagem)
    else:
        form = CadastroForm()

    return render(request, 'core/cadastro.html', {'form': form})


@require_POST
@login_required
def logout_view(request):
    """Logout do usuário (somente POST: um link GET poderia deslogar a pessoa sem querer)"""
    logout(request)
    messages.info(request, 'Você saiu da sua conta.')
    return redirect('core:login')


# ===================== DASHBOARD =====================

@login_required
def dashboard(request):
    """Dashboard do usuário"""
    user = request.user
    hoje = timezone.localdate()  # data local (America/Sao_Paulo), não UTC
    atualizar_status_metas(user)

    materias = Materia.objects.filter(usuario=user)
    atividades = Atividade.objects.filter(usuario=user)
    metas = Meta.objects.filter(usuario=user)

    total_materias = materias.count()
    total_atividades = atividades.count()
    progresso_medio = round(materias.aggregate(m=Avg('progresso'))['m'] or 0)

    atividades_hoje = (
        atividades.filter(data=hoje)
        .select_related('materia')
        .order_by('hora_inicio')
    )

    metas_abertas = metas.exclude(status='completed')
    metas_ativas = metas_abertas.order_by('-progresso_atual')[:5]
    total_metas = metas_abertas.count()

    atividades_concluidas = atividades.filter(concluida=True).count()
    metas_concluidas = metas.filter(status='completed').count()
    horas_concluidas = sum(a.get_duracao() for a in atividades.filter(concluida=True))
    pontos = atividades_concluidas * 10 + metas_concluidas * 15 + round(horas_concluidas) * 20
    nivel, proximo_limiar, nivel_progresso = calcular_nivel(pontos)

    context = {
        'user': user,
        'total_materias': total_materias,
        'total_atividades': total_atividades,
        'total_metas': total_metas,
        'progresso_medio': progresso_medio,
        'atividades_hoje': atividades_hoje,
        'metas_ativas': metas_ativas,
        'atividades_concluidas': atividades_concluidas,
        'nivel': nivel,
        'pontos': pontos,
        'proximo_limiar': proximo_limiar,
        'nivel_progresso': nivel_progresso,
    }
    return render(request, 'core/dashboard.html', context)


# ===================== PERFIL / AVATAR =====================

@require_POST
@login_required
def upload_avatar(request):
    """Upload da foto de perfil, com validação de tamanho e de tipo real da imagem"""
    arquivo = request.FILES.get('avatar')
    if not arquivo:
        return JsonResponse({'success': False, 'message': 'Nenhuma imagem enviada.'}, status=400)

    if arquivo.size > AVATAR_MAX_BYTES:
        return JsonResponse(
            {'success': False, 'message': 'A imagem deve ter no máximo 2 MB.'}, status=400
        )

    # Confere o conteúdo de verdade (não só a extensão/Content-Type informados pelo navegador)
    try:
        from PIL import Image
        with Image.open(arquivo) as img:
            formato = img.format
            img.verify()
    except Exception:
        return JsonResponse(
            {'success': False, 'message': 'O arquivo enviado não é uma imagem válida.'}, status=400
        )
    if formato not in AVATAR_FORMATOS:
        return JsonResponse(
            {'success': False, 'message': 'Use uma imagem JPG, PNG, WEBP ou GIF.'}, status=400
        )
    arquivo.seek(0)

    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    if perfil.avatar:
        perfil.avatar.delete(save=False)  # não acumula fotos antigas em media/
    perfil.avatar = arquivo
    perfil.save()
    return JsonResponse({
        'success': True,
        'message': 'Foto atualizada com sucesso!',
        'url': perfil.avatar.url,
    })


# ===================== MATÉRIAS =====================

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
        for mensagem in erros_do_form(form):
            messages.error(request, mensagem)
    else:
        form = MateriaForm()

    # Prioridade em ordem lógica (Alta > Média > Baixa). Ordenar pelo texto
    # ('high','medium','low') colocava "Média" antes de "Alta".
    ordem_prioridade = Case(
        When(prioridade='high', then=Value(0)),
        When(prioridade='medium', then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    materias = Materia.objects.filter(usuario=user).order_by(ordem_prioridade, 'nome')

    return render(request, 'core/materias.html', {'form': form, 'materias': materias})


@require_POST
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
        data = ler_json(request)
        if data is None:
            return JsonResponse({'success': False, 'message': 'Dados inválidos.'}, status=400)

        # Campos ausentes mantêm o valor atual; tudo passa pela validação do MateriaForm
        campos = ['nome', 'professor', 'topicos', 'carga_horaria', 'prioridade', 'progresso']
        dados = {c: data.get(c, getattr(materia, c)) for c in campos}
        form = MateriaForm(dados, instance=materia)
        if form.is_valid():
            materia = form.save(commit=False)
            materia.emoji = get_emoji_for_subject(materia.nome)
            materia.save()
            return JsonResponse({'success': True})
        return JsonResponse(
            {'success': False, 'message': ' '.join(erros_do_form(form))}, status=400
        )

    return JsonResponse({'error': 'Método não permitido'}, status=405)


# ===================== CRONOGRAMA =====================

@login_required
def cronogramas_view(request):
    """Página de cronograma. Cada atividade pertence a uma data (e, portanto, a uma semana)."""
    user = request.user
    materias_do_usuario = Materia.objects.filter(usuario=user)

    # Semana exibida (?semana=0 atual; negativo = passadas, positivo = futuras)
    hoje = timezone.localdate()
    try:
        semana_offset = max(-520, min(520, int(request.GET.get('semana', 0))))
    except (TypeError, ValueError):
        semana_offset = 0
    inicio_semana = hoje - timedelta(days=hoje.weekday()) + timedelta(weeks=semana_offset)
    fim_semana = inicio_semana + timedelta(days=6)

    if request.method == 'POST':
        form = AtividadeForm(request.POST)
        form.fields['materia'].queryset = materias_do_usuario
        if form.is_valid():
            atividade = form.save(commit=False)
            atividade.usuario = user
            # A atividade vai para a semana que está sendo exibida, no dia escolhido
            atividade.data = inicio_semana + timedelta(days=atividade.dia_semana)
            atividade.save()
            messages.success(request, f'Atividade "{atividade.titulo}" criada com sucesso!')
            return redirect(f"{reverse('core:cronogramas')}?semana={semana_offset}")
        for mensagem in erros_do_form(form):
            messages.error(request, mensagem)
    else:
        form = AtividadeForm()
        form.fields['materia'].queryset = materias_do_usuario

    label_semana = '%d %s – %d %s %d' % (
        inicio_semana.day, MESES_ABREV[inicio_semana.month - 1],
        fim_semana.day, MESES_ABREV[fim_semana.month - 1], fim_semana.year
    )

    # Só as atividades DESTA semana (uma consulta; agrupamento por dia em Python)
    trabalhos = list(
        Atividade.objects.filter(usuario=user, data__range=(inicio_semana, fim_semana))
        .select_related('materia')
        .order_by('data', 'hora_inicio')
    )
    por_dia = {i: [] for i in range(7)}
    for atividade in trabalhos:
        por_dia[atividade.data.weekday()].append(atividade)

    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    semana = []
    for i, dia in enumerate(dias_semana):
        dia_data = inicio_semana + timedelta(days=i)
        semana.append((
            dia,
            por_dia[i],
            {
                'data_iso': dia_data.isoformat(),
                'data_texto': '%d %s' % (dia_data.day, MESES_ABREV[dia_data.month - 1]),
                'eh_hoje': dia_data == hoje,
            },
        ))

    total_atividades = len(trabalhos)
    concluidas = sum(1 for a in trabalhos if a.concluida)
    taxa_conclusao = round(concluidas * 100 / total_atividades) if total_atividades else 0
    # Horas de estudo = soma da duração das atividades CONCLUÍDAS da semana exibida
    horas_semana = round(sum(a.get_duracao() for a in trabalhos if a.concluida), 1)

    context = {
        'form': form,
        'semana': semana,
        'dias_semana': dias_semana,
        'label_semana': label_semana,
        'semana_offset': semana_offset,
        'materias': materias_do_usuario.order_by('nome'),
        'hoje': hoje.weekday(),
        'total_atividades': total_atividades,
        'total_materias': materias_do_usuario.count(),
        'taxa_conclusao': taxa_conclusao,
        'horas_semana': horas_semana,
    }
    return render(request, 'core/cronogramas.html', context)


@require_POST
@login_required
def atividade_toggle(request, pk):
    """Concluir / reabrir atividade"""
    atividade = get_object_or_404(Atividade, pk=pk, usuario=request.user)
    atividade.concluida = not atividade.concluida
    atividade.save(update_fields=['concluida'])
    if atividade.concluida:
        messages.success(request, f'Atividade "{atividade.titulo}" concluída. Continue assim!')
    else:
        messages.info(request, f'Atividade "{atividade.titulo}" reaberta.')
    return redirect(destino_seguro(request, 'core:cronogramas'))


@require_POST
@login_required
def atividade_delete(request, pk):
    """Excluir atividade"""
    atividade = get_object_or_404(Atividade, pk=pk, usuario=request.user)
    titulo = atividade.titulo
    atividade.delete()
    messages.success(request, f'Atividade "{titulo}" excluída com sucesso.')
    return redirect(destino_seguro(request, 'core:cronogramas'))


# ===================== METAS =====================

@login_required
def metas_view(request):
    """Página de metas"""
    user = request.user
    materias_do_usuario = Materia.objects.filter(usuario=user)

    if request.method == 'POST':
        form = MetaForm(request.POST)
        form.fields['materia'].queryset = materias_do_usuario
        if form.is_valid():
            meta = form.save(commit=False)
            meta.usuario = user
            meta.status = meta.calcular_status()
            meta.save()
            messages.success(request, f'Meta "{meta.titulo}" criada com sucesso!')
            return redirect('core:metas')
        for mensagem in erros_do_form(form):
            messages.error(request, mensagem)
    else:
        form = MetaForm()
        form.fields['materia'].queryset = materias_do_usuario

    atualizar_status_metas(user)
    metas = Meta.objects.filter(usuario=user).select_related('materia').order_by('-data_criacao')

    context = {
        'form': form,
        'metas': metas,
        'materias': materias_do_usuario.order_by('nome'),
    }
    return render(request, 'core/metas.html', context)


@require_POST
@login_required
def meta_delete(request, pk):
    """Excluir meta"""
    meta = get_object_or_404(Meta, pk=pk, usuario=request.user)
    titulo = meta.titulo
    meta.delete()
    messages.success(request, f'Meta "{titulo}" excluída com sucesso.')
    return redirect('core:metas')


@login_required
def meta_edit(request, pk):
    """Editar meta (GET para buscar dados, POST para salvar)"""
    meta = get_object_or_404(Meta, pk=pk, usuario=request.user)

    if request.method == 'GET':
        return JsonResponse({
            'id': meta.id,
            'titulo': meta.titulo,
            'materia': meta.materia_id or '',
            'descricao': meta.descricao or '',
            'meta_progresso': meta.meta_progresso,
            'progresso_atual': meta.progresso_atual,
            'prazo': meta.prazo.strftime('%Y-%m-%d') if meta.prazo else '',
            'status': meta.status,
        })

    if request.method == 'POST':
        json_mode = eh_json(request)
        data = ler_json(request) if json_mode else request.POST
        if data is None:
            return JsonResponse({'success': False, 'message': 'Dados inválidos.'}, status=400)

        # Campos ausentes mantêm o valor atual. A matéria só pode ser uma do próprio usuário
        # (antes qualquer id era aceito, inclusive de outras contas).
        dados = {
            'titulo': data.get('titulo', meta.titulo),
            'descricao': data.get('descricao', meta.descricao or ''),
            'meta_progresso': data.get('meta_progresso', meta.meta_progresso),
            'progresso_atual': data.get('progresso_atual', meta.progresso_atual),
            'prazo': data.get('prazo', meta.prazo.isoformat() if meta.prazo else ''),
            'materia': data.get('materia', meta.materia_id or ''),
        }
        form = MetaForm(dados, instance=meta)
        form.fields['materia'].queryset = Materia.objects.filter(usuario=request.user)
        if form.is_valid():
            meta = form.save(commit=False)
            meta.status = meta.calcular_status()
            meta.save()
            if json_mode:
                return JsonResponse({'success': True})
            messages.success(request, f'Meta "{meta.titulo}" atualizada com sucesso!')
            return redirect('core:metas')

        if json_mode:
            return JsonResponse(
                {'success': False, 'message': ' '.join(erros_do_form(form))}, status=400
            )
        for mensagem in erros_do_form(form):
            messages.error(request, mensagem)
        return redirect('core:metas')

    return JsonResponse({'error': 'Método não permitido'}, status=405)


# ===================== RELATÓRIOS =====================

@login_required
def relatorios_view(request):
    """Página de relatórios.

    Regras:
    - Horas estudadas = soma da duração das atividades CONCLUÍDAS no cronograma
      (dentro do período escolhido, pela data em que foram concluídas).
    - Atividades concluídas = atividades do cronograma + metas concluídas.
    - Matérias = as matérias cadastradas do usuário (adicionar/excluir reflete aqui).
    """
    user = request.user
    atualizar_status_metas(user)

    # Filtro de período (?periodo=hoje|semana|mes|ult_mes|tudo)
    janelas = {'hoje': 0, 'semana': 6, 'mes': 29, 'ult_mes': 59}
    periodo = request.GET.get('periodo', 'semana')
    if periodo not in janelas and periodo != 'tudo':
        periodo = 'semana'
    hoje = timezone.localdate()
    dias_janela = janelas.get(periodo)
    inicio_periodo = hoje - timedelta(days=dias_janela) if dias_janela is not None else None

    # Matérias cadastradas (somem daqui ao serem excluídas na página Matérias)
    materias_qs = Materia.objects.filter(usuario=user)
    total_materias = materias_qs.count()
    total_atividades = Atividade.objects.filter(usuario=user).count()
    total_metas = Meta.objects.filter(usuario=user).count()
    progresso_medio = round(materias_qs.aggregate(m=Avg('progresso'))['m'] or 0)

    # Concluídas: atividades do cronograma + metas concluídas
    concluidas_qs = Atividade.objects.filter(usuario=user, concluida=True).select_related('materia')
    metas_concluidas = Meta.objects.filter(usuario=user, status='completed').count()
    atividades_concluidas = concluidas_qs.count() + metas_concluidas

    # ===== HORAS ESTUDADAS (atividades concluídas no período) =====
    no_periodo = concluidas_qs
    if inicio_periodo is not None:
        no_periodo = no_periodo.filter(data_conclusao__gte=inicio_periodo)
    lista = list(no_periodo.order_by('-data_conclusao', '-hora_inicio'))

    total_minutos = round(sum(a.get_duracao() for a in lista) * 60)
    horas_estudadas = round(total_minutos / 60, 1)

    # Distribuição por matéria (minutos de atividades concluídas no período)
    DIST_CORES = ['#2878FF', '#35DDF2', '#22B573', '#EE9B2E', '#E5484D', '#7c3aed', '#0891b2', '#d97706']
    acumulado = {}
    for a in lista:
        # Com matéria: agrupa pela matéria. Sem matéria: usa o título da atividade
        # (ex.: "Português") e agrupa atividades de mesmo título.
        if a.materia_id:
            chave, nome = a.materia_id, a.materia.nome
        else:
            chave, nome = ('titulo', a.titulo.strip().lower()), a.titulo.strip() or 'Sem matéria'
        item = acumulado.setdefault(chave, {
            'nome': nome,
            'emoji': (a.materia.emoji if a.materia else '') or '',
            'minutos': 0,
        })
        item['minutos'] += round(a.get_duracao() * 60)
    total_dist = total_minutos or 1
    distribuicao = []
    for i, item in enumerate(sorted(acumulado.values(), key=lambda x: -x['minutos'])):
        item['pct'] = round(item['minutos'] * 100 / total_dist)
        item['cor'] = DIST_CORES[i % len(DIST_CORES)]
        distribuicao.append(item)
    materias_estudadas = len([k for k in acumulado if not isinstance(k, tuple)])

    # Ranking por matéria
    materias = materias_qs.order_by('-progresso', 'nome')

    # Atividades concluídas recentes (do período)
    registros_recentes = [
        {
            'titulo': a.titulo,
            'materia': a.materia.nome if a.materia else 'Sem matéria',
            'minutos': round(a.get_duracao() * 60),
            'data': a.data_conclusao,
            'hora_inicio': a.hora_inicio,
        }
        for a in lista[:10]
    ]

    # Gráfico dos últimos 7 dias, por data de conclusão
    inicio_grafico = hoje - timedelta(days=6)
    horas_por_data = {}
    for a in concluidas_qs.filter(data_conclusao__gte=inicio_grafico):
        horas_por_data[a.data_conclusao] = horas_por_data.get(a.data_conclusao, 0) + a.get_duracao()
    grafico = []
    for i in range(6, -1, -1):
        dia = hoje - timedelta(days=i)
        grafico.append({
            'dia': DIAS_ABREV[dia.weekday()],
            'horas': round(horas_por_data.get(dia, 0), 1),
            'eh_hoje': dia == hoje,
        })
    maior = max((g['horas'] for g in grafico), default=0)
    for g in grafico:
        # altura proporcional ao maior dia (máx. 80% para sobrar espaço aos rótulos)
        g['pct'] = max(6, round(g['horas'] * 80 / maior)) if g['horas'] > 0 and maior else 0

    context = {
        'periodo': periodo,
        'total_materias': total_materias,
        'total_atividades': total_atividades,
        'total_metas': total_metas,
        'progresso_medio': progresso_medio,
        'atividades_concluidas': atividades_concluidas,
        'horas_estudadas': horas_estudadas,
        'materias_estudadas': materias_estudadas,
        'materias': materias,
        'distribuicao': distribuicao,
        'registros_recentes': registros_recentes,
        'grafico': grafico,
    }
    return render(request, 'core/relatorios.html', context)


# ===================== CONFIGURAÇÕES =====================

def _resposta_erro(request, json_mode, mensagem, destino='core:configuracoes'):
    if json_mode:
        return JsonResponse({'success': False, 'message': mensagem}, status=400)
    messages.error(request, mensagem)
    return redirect(destino)


@login_required
def configuracoes_view(request):
    """Página de configurações"""
    user = request.user
    perfil, _ = Perfil.objects.get_or_create(usuario=user)
    config, _ = Configuracao.objects.get_or_create(usuario=user)

    if request.method == 'POST':
        json_mode = eh_json(request)
        data = ler_json(request) if json_mode else request.POST
        if data is None:
            return _resposta_erro(request, json_mode, 'Dados inválidos.')

        # ---------- Validação (nada é gravado se algo estiver errado) ----------
        novo_email = None
        if 'email' in data:
            novo_email = str(data['email']).strip().lower()
            try:
                validate_email(novo_email)
            except ValidationError:
                return _resposta_erro(request, json_mode, 'Informe um e-mail válido.')
            em_uso = User.objects.exclude(pk=user.pk).filter(
                Q(email__iexact=novo_email) | Q(username__iexact=novo_email)
            ).exists()
            if em_uso:
                return _resposta_erro(request, json_mode, 'Este e-mail já está em uso por outra conta.')

        nascimento = None
        if data.get('data_nascimento'):
            try:
                nascimento = datetime.strptime(str(data['data_nascimento']), '%Y-%m-%d').date()
            except ValueError:
                return _resposta_erro(request, json_mode, 'Data de nascimento inválida.')
            if nascimento > timezone.localdate():
                return _resposta_erro(request, json_mode, 'A data de nascimento não pode estar no futuro.')

        if 'objetivo' in data and data['objetivo'] not in dict(Perfil.OBJETIVO_CHOICES):
            return _resposta_erro(request, json_mode, 'Objetivo inválido.')
        if data.get('serie') and data['serie'] not in dict(Perfil.SERIE_CHOICES):
            return _resposta_erro(request, json_mode, 'Série inválida.')
        if 'tema' in data and data['tema'] not in TEMAS_VALIDOS:
            return _resposta_erro(request, json_mode, 'Tema inválido.')

        cor = None
        if 'cor_primaria' in data:
            cor = normalizar_cor(data['cor_primaria'])
            if cor is None:
                return _resposta_erro(request, json_mode, 'Cor inválida.')

        for campo, limite in (('nome', 150), ('telefone', 20), ('instituicao', 200)):
            if campo in data and len(str(data[campo])) > limite:
                return _resposta_erro(request, json_mode, f'O campo "{campo}" aceita até {limite} caracteres.')

        # ---------- Gravação ----------
        with transaction.atomic():
            if 'nome' in data:
                user.first_name = str(data['nome']).strip()
            if novo_email is not None and novo_email != (user.email or '').lower():
                # O login é feito por e-mail e o username é o próprio e-mail. Se só o e-mail
                # mudasse, a pessoa não conseguiria mais entrar com o endereço novo.
                if user.username.lower() == (user.email or '').lower():
                    user.username = novo_email
                user.email = novo_email
            user.save()

            if 'telefone' in data:
                perfil.telefone = str(data['telefone']).strip()
            if nascimento:
                perfil.data_nascimento = nascimento
            if 'instituicao' in data:
                perfil.instituicao = str(data['instituicao']).strip()
            if 'serie' in data:
                perfil.serie = data['serie'] or None
            if 'objetivo' in data:
                perfil.objetivo = data['objetivo']
            perfil.save()

            if 'tema' in data:
                config.tema = data['tema']
            if cor:
                config.cor_primaria = cor
            for campo in ('notificacoes_email', 'notificacoes_push', 'lembrete_diario', 'alerta_metas_atrasadas'):
                if campo in data:
                    setattr(config, campo, str(data[campo]).lower() in ('true', '1', 'on'))
            config.save()

        if json_mode:
            return JsonResponse({'success': True, 'message': 'Configurações salvas com sucesso!'})
        messages.success(request, 'Configurações salvas com sucesso!')
        return redirect('core:configuracoes')

    return render(request, 'core/configuracoes.html', {'perfil': perfil, 'config': config, 'user': user})


@require_POST
@login_required
def config_salvar_tudo(request):
    """Salvar configurações de aparência/notificações (AJAX)"""
    data = ler_json(request)
    if data is None:
        return JsonResponse({'success': False, 'message': 'Dados inválidos.'}, status=400)

    config, _ = Configuracao.objects.get_or_create(usuario=request.user)

    if 'tema' in data:
        if data['tema'] not in TEMAS_VALIDOS:
            return JsonResponse({'success': False, 'message': 'Tema inválido.'}, status=400)
        config.tema = data['tema']
    if 'cor_primaria' in data:
        cor = normalizar_cor(data['cor_primaria'])
        if cor is None:
            return JsonResponse({'success': False, 'message': 'Cor inválida.'}, status=400)
        config.cor_primaria = cor
    for campo in ('notificacoes_email', 'notificacoes_push', 'lembrete_diario', 'alerta_metas_atrasadas'):
        if campo in data:
            setattr(config, campo, str(data[campo]).lower() in ('true', '1', 'on'))

    config.save()
    return JsonResponse({'success': True})


@require_POST
@login_required
def alterar_senha(request):
    """Troca a senha do usuário (senha atual + nova senha confirmada)."""
    json_mode = eh_json(request)
    data = ler_json(request) if json_mode else request.POST
    if data is None:
        return _resposta_erro(request, json_mode, 'Dados inválidos.')

    form = PasswordChangeForm(request.user, data={
        'old_password': data.get('old_password', ''),
        'new_password1': data.get('new_password1', ''),
        'new_password2': data.get('new_password2', ''),
    })
    if form.is_valid():
        form.save()
        # Mantém o usuário logado após a troca (senão a sessão é invalidada)
        update_session_auth_hash(request, form.user)
        if json_mode:
            return JsonResponse({'success': True, 'message': 'Senha alterada com sucesso!'})
        messages.success(request, 'Senha alterada com sucesso!')
        return redirect('core:configuracoes')

    return _resposta_erro(request, json_mode, ' '.join(erros_do_form(form)) or 'Não foi possível alterar a senha.')


@login_required
def exportar_dados(request):
    """Baixa um JSON com todos os dados do usuário (Privacidade)."""
    user = request.user
    perfil, _ = Perfil.objects.get_or_create(usuario=user)
    config, _ = Configuracao.objects.get_or_create(usuario=user)

    dados = {
        'usuario': {
            'nome': user.get_full_name(),
            'email': user.email,
            'data_cadastro': user.date_joined.isoformat(),
        },
        'perfil': {
            'telefone': perfil.telefone or '',
            'data_nascimento': perfil.data_nascimento.isoformat() if perfil.data_nascimento else None,
            'instituicao': perfil.instituicao or '',
            'serie': perfil.serie or '',
            'objetivo': perfil.objetivo,
        },
        'configuracao': {
            'tema': config.tema,
            'cor_primaria': config.cor_primaria,
        },
        'materias': [
            {
                'nome': m.nome,
                'professor': m.professor or '',
                'topicos': m.topicos or '',
                'carga_horaria': m.carga_horaria,
                'prioridade': m.prioridade,
                'progresso': m.progresso,
            }
            for m in Materia.objects.filter(usuario=user)
        ],
        'atividades': [
            {
                'titulo': a.titulo,
                'materia': a.materia.nome if a.materia else None,
                'data': a.data.isoformat() if a.data else None,
                'hora_inicio': a.hora_inicio.strftime('%H:%M'),
                'hora_fim': a.hora_fim.strftime('%H:%M'),
                'concluida': a.concluida,
                'data_conclusao': a.data_conclusao.isoformat() if a.data_conclusao else None,
            }
            for a in Atividade.objects.filter(usuario=user).select_related('materia')
        ],
        'metas': [
            {
                'titulo': m.titulo,
                'materia': m.materia.nome if m.materia else None,
                'meta_progresso': m.meta_progresso,
                'progresso_atual': m.progresso_atual,
                'prazo': m.prazo.isoformat() if m.prazo else None,
                'status': m.status,
            }
            for m in Meta.objects.filter(usuario=user).select_related('materia')
        ],
    }

    response = JsonResponse(dados, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="sioe-meus-dados.json"'
    return response


@require_POST
@login_required
def enviar_feedback(request):
    """Recebe o feedback do usuário (aba Privacidade)."""
    json_mode = eh_json(request)
    data = ler_json(request) if json_mode else request.POST
    if data is None:
        return _resposta_erro(request, json_mode, 'Dados inválidos.')

    mensagem = str(data.get('mensagem') or '').strip()
    if len(mensagem) < 5:
        return _resposta_erro(request, json_mode, 'Escreva uma mensagem com pelo menos 5 caracteres.')
    if len(mensagem) > 2000:
        return _resposta_erro(request, json_mode, 'A mensagem pode ter no máximo 2000 caracteres.')

    tipo = data.get('tipo') or 'sugestao'
    if tipo not in dict(Feedback.TIPO_CHOICES):
        tipo = 'sugestao'

    Feedback.objects.create(
        usuario=request.user,
        email=str(data.get('email') or request.user.email).strip(),
        tipo=tipo,
        mensagem=mensagem,
    )

    if json_mode:
        return JsonResponse({'success': True, 'message': 'Feedback enviado. Obrigado!'})
    messages.success(request, 'Feedback enviado. Obrigado pela ajuda!')
    return redirect('core:configuracoes')


@require_POST
@login_required
def excluir_conta(request):
    """Exclui a conta do usuário (exige digitar EXCLUIR para confirmar)."""
    if (request.POST.get('confirmacao') or '').strip().upper() != 'EXCLUIR':
        messages.error(request, 'Digite EXCLUIR para confirmar a exclusão da conta.')
        return redirect('core:configuracoes')

    usuario = request.user
    logout(request)
    usuario.delete()
    messages.info(request, 'Sua conta foi excluída.')
    return redirect('core:login')
