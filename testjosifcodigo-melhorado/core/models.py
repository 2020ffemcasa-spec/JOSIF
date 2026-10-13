from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Perfil(models.Model):
    OBJETIVO_CHOICES = [
        ('ENEM', 'ENEM'),
        ('VESTIBULAR', 'Vestibular'),
        ('CONCURSO', 'Concurso'),
        ('ESTUDOS_GERAIS', 'Estudos Gerais'),
    ]
    
    SERIE_CHOICES = [
        ('1EM', '1º Ano - Ensino Medio'),
        ('2EM', '2º Ano - Ensino Medio'),
        ('3EM', '3º Ano - Ensino Medio'),
        ('CURSINHO', 'Cursinho Pre-Vestibular'),
        ('SUPERIOR', 'Ensino Superior'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    data_nascimento = models.DateField('Data de Nascimento', blank=True, null=True)
    instituicao = models.CharField('Instituicao de Ensino', max_length=200, blank=True, null=True)
    serie = models.CharField('Serie', max_length=20, choices=SERIE_CHOICES, blank=True, null=True)
    objetivo = models.CharField('Objetivo', max_length=20, choices=OBJETIVO_CHOICES, default='ENEM')
    avatar = models.ImageField('Avatar', upload_to='avatars/', blank=True, null=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    
    def __str__(self):
        return f'Perfil de {self.usuario.username}'
    
    def get_iniciais(self):
        nome = self.usuario.get_full_name() or self.usuario.username
        partes = nome.split()
        if len(partes) >= 2:
            return f'{partes[0][0]}{partes[1][0]}'.upper()
        return nome[:2].upper()


class Materia(models.Model):
    PRIORIDADE_CHOICES = [
        ('high', 'Alta'),
        ('medium', 'Media'),
        ('low', 'Baixa'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='materias')
    nome = models.CharField('Nome da Materia', max_length=100)
    professor = models.CharField('Professor', max_length=100, blank=True, null=True)
    topicos = models.TextField('Topicos', blank=True, null=True)
    carga_horaria = models.PositiveIntegerField('Carga Horaria (h/semana)', default=4)
    prioridade = models.CharField('Prioridade', max_length=10, choices=PRIORIDADE_CHOICES, default='medium')
    progresso = models.PositiveIntegerField('Progresso (%)', default=0)
    emoji = models.CharField('Emoji', max_length=10, default='📖')
    data_criacao = models.DateTimeField('Data de Criacao', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Data de Atualizacao', auto_now=True)
    
    def __str__(self):
        return self.nome
    
    def get_progresso_color(self):
        if self.progresso >= 80:
            return 'linear-gradient(90deg,#2878FF,#17243A)'
        elif self.progresso >= 60:
            return 'linear-gradient(90deg,#22B573,#7EE2A8)'
        elif self.progresso >= 40:
            return 'linear-gradient(90deg,#EE9B2E,#F6C163)'
        return 'linear-gradient(90deg,#E5484D,#F07B80)'
    
    def get_prioridade_label(self):
        return dict(self.PRIORIDADE_CHOICES).get(self.prioridade, 'Media')


class Atividade(models.Model):
    DIAS_SEMANA = [
        (0, 'Segunda-feira'),
        (1, 'Terca-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sabado'),
        (6, 'Domingo'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='atividades')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='atividades', blank=True, null=True)
    titulo = models.CharField('Titulo', max_length=200)
    descricao = models.TextField('Descricao', blank=True, null=True)
    dia_semana = models.PositiveSmallIntegerField('Dia da Semana', choices=DIAS_SEMANA)
    hora_inicio = models.TimeField('Horario de Inicio')
    hora_fim = models.TimeField('Horario de Termino')
    # Data real da atividade: ela pertence a UMA semana (não se repete nas outras)
    data = models.DateField('Data', blank=True, null=True)
    concluida = models.BooleanField('Concluida', default=False)
    # Dia em que foi marcada como concluída (base dos relatórios de horas estudadas)
    data_conclusao = models.DateField('Data de Conclusao', blank=True, null=True)
    data_criacao = models.DateTimeField('Data de Criacao', auto_now_add=True)
    
    def __str__(self):
        return f'{self.titulo} - {self.get_dia_semana_display()}'

    def save(self, *args, **kwargs):
        # Sem data informada (ex.: admin/shell): usa o dia da semana escolhido na semana atual
        if self.data is None:
            hoje = timezone.localdate()
            self.data = hoje - timedelta(days=hoje.weekday()) + timedelta(days=self.dia_semana)
        # Mantém data_conclusao coerente com `concluida`, em qualquer lugar que salvar
        # (view, admin, shell).
        if self.concluida and not self.data_conclusao:
            self.data_conclusao = timezone.localdate()
        elif not self.concluida:
            self.data_conclusao = None
        campos = kwargs.get('update_fields')
        if campos is not None and 'concluida' in campos:
            kwargs['update_fields'] = list(set(campos) | {'data_conclusao'})
        super().save(*args, **kwargs)
    
    def get_duracao(self):
        """Duração em horas (float), considerando os minutos.

        Antes só a diferença entre as *horas cheias* era usada (09:00–09:45 dava 0h).
        Se o término for menor que o início, assume que passou da meia-noite.
        """
        inicio = self.hora_inicio.hour * 60 + self.hora_inicio.minute
        fim = self.hora_fim.hour * 60 + self.hora_fim.minute
        minutos = fim - inicio
        if minutos < 0:
            minutos += 24 * 60
        return round(minutos / 60, 2)


class Meta(models.Model):
    STATUS_CHOICES = [
        ('on-track', 'No Caminho'),
        ('at-risk', 'Em Risco'),
        ('behind', 'Atrasada'),
        ('completed', 'Concluida'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='metas')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='metas', blank=True, null=True)
    titulo = models.CharField('Titulo', max_length=200)
    descricao = models.TextField('Descricao', blank=True, null=True)
    meta_progresso = models.PositiveIntegerField('Meta de Progresso (%)', default=80)
    progresso_atual = models.PositiveIntegerField('Progresso Atual (%)', default=0)
    prazo = models.DateField('Prazo', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='on-track')
    data_criacao = models.DateTimeField('Data de Criacao', auto_now_add=True)
    
    def __str__(self):
        return f'{self.titulo} - {self.usuario.username}'
    
    def calcular_status(self):
        if self.progresso_atual >= self.meta_progresso:
            return 'completed'
        # Prazo vencido e meta não atingida => atrasada, independente do progresso
        if self.prazo and self.prazo < timezone.localdate():
            return 'behind'
        elif self.progresso_atual >= self.meta_progresso * 0.7:
            return 'on-track'
        elif self.progresso_atual >= self.meta_progresso * 0.4:
            return 'at-risk'
        return 'behind'
    
    def get_status_class(self):
        return self.status
    
    def get_progress_color(self):
        if self.status == 'completed' or self.progresso_atual >= self.meta_progresso:
            return 'linear-gradient(90deg,#22B573,#7EE2A8)'
        elif self.progresso_atual >= self.meta_progresso * 0.7:
            return 'linear-gradient(90deg,#22B573,#7EE2A8)'
        elif self.progresso_atual >= self.meta_progresso * 0.4:
            return 'linear-gradient(90deg,#EE9B2E,#F6C163)'
        return 'linear-gradient(90deg,#E5484D,#F07B80)'


class Configuracao(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='configuracao')
    tema = models.CharField('Tema', max_length=20, default='light')
    cor_primaria = models.CharField('Cor Primaria', max_length=20, default='#2878FF')
    notificacoes_email = models.BooleanField('Notificacoes por E-mail', default=True)
    notificacoes_push = models.BooleanField('Notificacoes Push', default=True)
    lembrete_diario = models.BooleanField('Lembrete Diario', default=True)
    alerta_metas_atrasadas = models.BooleanField('Alerta de Metas Atrasadas', default=True)

    def __str__(self):
        return f'Configuracao de {self.usuario.username}'

class RegistroEstudo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_estudo')
    materia = models.ForeignKey(Materia, on_delete=models.SET_NULL, related_name='registros_estudo', null=True, blank=True)
    # default (e não auto_now_add) para permitir registrar estudos de dias anteriores
    data = models.DateField('Data', default=timezone.localdate)
    hora_inicio = models.TimeField('Hora de Inicio', auto_now_add=True)
    duracao_minutos = models.PositiveIntegerField('Duracao (minutos)', default=0)
    
    def __str__(self):
        return f'Estudo - {self.data}'


class Feedback(models.Model):
    TIPO_CHOICES = [
        ('sugestao', 'Sugestão'),
        ('bug', 'Problema'),
        ('elogio', 'Elogio'),
        ('outro', 'Outro'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='feedbacks', null=True, blank=True)
    email = models.EmailField('E-mail de contato', blank=True)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='sugestao')
    mensagem = models.TextField('Mensagem')
    data_criacao = models.DateTimeField('Data de Criacao', auto_now_add=True)

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.usuario or "anônimo"}'
