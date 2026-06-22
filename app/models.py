from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class AreaSaber(models.Model):
    nome = models.CharField('Nome', max_length=100)
    descricao = models.TextField('Descrição', blank=True, null=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Área do Saber'
        verbose_name_plural = 'Áreas do Saber'
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Perfil(models.Model):
    """Modelo para armazenar informações adicionais do usuário"""
    
    OBJETIVO_CHOICES = [
        ('ENEM', 'ENEM'),
        ('VESTIBULAR', 'Vestibular'),
        ('CONCURSO', 'Concurso'),
        ('ESTUDOS_GERAIS', 'Estudos Gerais'),
    ]
    
    SERIE_CHOICES = [
        ('1EM', '1º Ano - Ensino Médio'),
        ('2EM', '2º Ano - Ensino Médio'),
        ('3EM', '3º Ano - Ensino Médio'),
        ('CURSINHO', 'Cursinho Pré-Vestibular'),
        ('SUPERIOR', 'Ensino Superior'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    data_nascimento = models.DateField('Data de Nascimento', blank=True, null=True)
    instituicao = models.CharField('Instituição de Ensino', max_length=200, blank=True, null=True)
    serie = models.CharField('Série', max_length=20, choices=SERIE_CHOICES, blank=True, null=True)
    objetivo = models.CharField('Objetivo', max_length=20, choices=OBJETIVO_CHOICES, default='ENEM')
    avatar = models.ImageField('Avatar', upload_to='avatars/', blank=True, null=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'
    
    def __str__(self):
        return f'Perfil de {self.usuario.username}'
    
    def get_iniciais(self):
        """Retorna as iniciais do nome do usuário"""
        nome = self.usuario.get_full_name() or self.usuario.username
        partes = nome.split()
        if len(partes) >= 2:
            return f'{partes[0][0]}{partes[1][0]}'.upper()
        return nome[:2].upper()


class Materia(models.Model):
    """Modelo para matérias de estudo"""
    
    PRIORIDADE_CHOICES = [
        ('high', 'Alta'),
        ('medium', 'Média'),
        ('low', 'Baixa'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='materias')
    nome = models.CharField('Nome da Matéria', max_length=100)
    professor = models.CharField('Professor', max_length=100, blank=True, null=True)
    topicos = models.TextField('Tópicos', blank=True, null=True)
    carga_horaria = models.PositiveIntegerField('Carga Horária (h/semana)', default=4)
    prioridade = models.CharField('Prioridade', max_length=10, choices=PRIORIDADE_CHOICES, default='medium')
    progresso = models.PositiveIntegerField('Progresso (%)', default=0)
    cor = models.CharField('Cor', max_length=20, default='#2563eb')
    emoji = models.CharField('Emoji', max_length=10, default='📖')
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Matéria'
        verbose_name_plural = 'Matérias'
        ordering = ['-prioridade', 'nome']
    
    def __str__(self):
        return f'{self.nome} - {self.usuario.username}'
    
    def get_progresso_color(self):
        """Retorna a cor baseada no progresso"""
        if self.progresso >= 80:
            return 'linear-gradient(90deg,#2563eb,#4a7a9c)'
        elif self.progresso >= 60:
            return 'linear-gradient(90deg,#16a34a,#4ade80)'
        elif self.progresso >= 40:
            return 'linear-gradient(90deg,#ca8a04,#eab308)'
        return 'linear-gradient(90deg,#dc2626,#ef4444)'
    
    def get_prioridade_label(self):
        """Retorna o label da prioridade"""
        return dict(self.PRIORIDADE_CHOICES).get(self.prioridade, 'Média')


class Atividade(models.Model):
    """Modelo para atividades do cronograma"""
    
    DIAS_SEMANA = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='atividades')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='atividades', blank=True, null=True)
    titulo = models.CharField('Título', max_length=200)
    descricao = models.TextField('Descrição', blank=True, null=True)
    dia_semana = models.PositiveSmallIntegerField('Dia da Semana', choices=DIAS_SEMANA)
    hora_inicio = models.TimeField('Horário de Início')
    hora_fim = models.TimeField('Horário de Término')
    cor = models.CharField('Cor', max_length=20, default='#2563eb')
    concluida = models.BooleanField('Concluída', default=False)
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Atividade'
        verbose_name_plural = 'Atividades'
        ordering = ['dia_semana', 'hora_inicio']
    
    def __str__(self):
        return f'{self.titulo} - {self.get_dia_semana_display()}'
    
    def get_duracao(self):
        """Retorna a duração em horas"""
        delta = (self.hora_fim.hour - self.hora_inicio.hour)
        return delta
    
    def get_subject_emoji(self):
        """Retorna emoji baseado na matéria"""
        if self.materia and self.materia.emoji:
            return self.materia.emoji
        return '📖'
    
    def get_subject_name(self):
        """Retorna nome da matéria"""
        if self.materia:
            return self.materia.nome
        return 'Sem matéria'


class Meta(models.Model):
    """Modelo para metas de estudo"""
    
    STATUS_CHOICES = [
        ('on-track', '✅ No Caminho'),
        ('at-risk', '⚠️ Em Risco'),
        ('behind', '🔴 Atrasada'),
        ('completed', '✅ Concluída'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='metas')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='metas', blank=True, null=True)
    titulo = models.CharField('Título', max_length=200)
    descricao = models.TextField('Descrição', blank=True, null=True)
    meta_progresso = models.PositiveIntegerField('Meta de Progresso (%)', default=80)
    progresso_atual = models.PositiveIntegerField('Progresso Atual (%)', default=0)
    prazo = models.DateField('Prazo', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='on-track')
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Data de Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Meta'
        verbose_name_plural = 'Metas'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f'{self.titulo} - {self.usuario.username}'
    
    def calcular_status(self):
        """Calcula o status baseado no progresso"""
        if self.progresso_atual >= self.meta_progresso:
            return 'completed'
        elif self.progresso_atual >= self.meta_progresso * 0.7:
            return 'on-track'
        elif self.progresso_atual >= self.meta_progresso * 0.4:
            return 'at-risk'
        return 'behind'
    
    def get_status_class(self):
        """Retorna classe CSS para o status"""
        return self.status
    
    def get_progress_color(self):
        """Retorna cor baseada no progresso"""
        if self.status == 'completed' or self.progresso_atual >= self.meta_progresso:
            return 'linear-gradient(90deg,#16a34a,#4ade80)'
        elif self.progresso_atual >= self.meta_progresso * 0.7:
            return 'linear-gradient(90deg,#16a34a,#4ade80)'
        elif self.progresso_atual >= self.meta_progresso * 0.4:
            return 'linear-gradient(90deg,#ca8a04,#eab308)'
        return 'linear-gradient(90deg,#dc2626,#ef4444)'


class Configuracao(models.Model):
    """Modelo para configurações do usuário"""
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='configuracao')
    tema = models.CharField('Tema', max_length=20, default='light')
    cor_primaria = models.CharField('Cor Primária', max_length=20, default='#2563eb')
    tamanho_fonte = models.CharField('Tamanho da Fonte', max_length=20, default='medio')
    densidade_layout = models.CharField('Densidade do Layout', max_length=20, default='confortavel')
    notificacoes_email = models.BooleanField('Notificações por E-mail', default=True)
    notificacoes_push = models.BooleanField('Notificações Push', default=True)
    sons_notificacao = models.BooleanField('Sons de Notificação', default=False)
    lembrete_diario = models.BooleanField('Lembrete Diário', default=True)
    alerta_metas_atrasadas = models.BooleanField('Alerta de Metas Atrasadas', default=True)
    resumo_semanal = models.BooleanField('Resumo Semanal', default=True)
    lembrete_atividades = models.BooleanField('Lembrete Antes das Atividades', default=False)
    horario_lembrete = models.TimeField('Horário do Lembrete', default='07:30')
    perfil_publico = models.BooleanField('Perfil Público', default=False)
    mostrar_ranking = models.BooleanField('Mostrar no Ranking', default=True)
    coletar_dados = models.BooleanField('Coletar Dados de Uso', default=True)
    
    class Meta:
        verbose_name = 'Configuração'
        verbose_name_plural = 'Configurações'
    
    def __str__(self):
        return f'Configuração de {self.usuario.username}'


class RegistroEstudo(models.Model):
    """Modelo para registrar sessões de estudo"""
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_estudo')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='registros_estudo')
    data = models.DateField('Data', auto_now_add=True)
    hora_inicio = models.TimeField('Hora de Início', auto_now_add=True)
    hora_fim = models.TimeField('Hora de Fim', blank=True, null=True)
    duracao_minutos = models.PositiveIntegerField('Duração (minutos)', default=0)
    anotacoes = models.TextField('Anotações', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Registro de Estudo'
        verbose_name_plural = 'Registros de Estudo'
        ordering = ['-data', '-hora_inicio']
    
    def __str__(self):
        return f'Estudo de {self.materia.nome} - {self.data}'
    
    def save(self, *args, **kwargs):
        if self.hora_fim and self.hora_inicio:
            delta = (self.hora_fim.hour - self.hora_inicio.hour) * 60
            delta += (self.hora_fim.minute - self.hora_inicio.minute)
            self.duracao_minutos = max(0, delta)
        super().save(*args, **kwargs)