from django.db import models
from django.contrib.auth.models import User


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
            return 'linear-gradient(90deg,#2563eb,#4a7a9c)'
        elif self.progresso >= 60:
            return 'linear-gradient(90deg,#16a34a,#4ade80)'
        elif self.progresso >= 40:
            return 'linear-gradient(90deg,#ca8a04,#eab308)'
        return 'linear-gradient(90deg,#dc2626,#ef4444)'
    
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
    concluida = models.BooleanField('Concluida', default=False)
    data_criacao = models.DateTimeField('Data de Criacao', auto_now_add=True)
    
    def __str__(self):
        return f'{self.titulo} - {self.get_dia_semana_display()}'
    
    def get_duracao(self):
        delta = (self.hora_fim.hour - self.hora_inicio.hour)
        return delta


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
        elif self.progresso_atual >= self.meta_progresso * 0.7:
            return 'on-track'
        elif self.progresso_atual >= self.meta_progresso * 0.4:
            return 'at-risk'
        return 'behind'
    
    def get_status_class(self):
        return self.status
    
    def get_progress_color(self):
        if self.status == 'completed' or self.progresso_atual >= self.meta_progresso:
            return 'linear-gradient(90deg,#16a34a,#4ade80)'
        elif self.progresso_atual >= self.meta_progresso * 0.7:
            return 'linear-gradient(90deg,#16a34a,#4ade80)'
        elif self.progresso_atual >= self.meta_progresso * 0.4:
            return 'linear-gradient(90deg,#ca8a04,#eab308)'
        return 'linear-gradient(90deg,#dc2626,#ef4444)'


class Configuracao(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='configuracao')
    tema = models.CharField('Tema', max_length=20, default='light')
    cor_primaria = models.CharField('Cor Primaria', max_length=20, default='#2563eb')
    notificacoes_email = models.BooleanField('Notificacoes por E-mail', default=True)
    notificacoes_push = models.BooleanField('Notificacoes Push', default=True)
    lembrete_diario = models.BooleanField('Lembrete Diario', default=True)
    alerta_metas_atrasadas = models.BooleanField('Alerta de Metas Atrasadas', default=True)
    
    def __str__(self):
        return f'Configuracao de {self.usuario.username}'

class RegistroEstudo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_estudo')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='registros_estudo')
    data = models.DateField('Data', auto_now_add=True)
    hora_inicio = models.TimeField('Hora de Inicio', auto_now_add=True)
    duracao_minutos = models.PositiveIntegerField('Duracao (minutos)', default=0)
    
    def __str__(self):
        return f'Estudo de {self.materia.nome} - {self.data}'