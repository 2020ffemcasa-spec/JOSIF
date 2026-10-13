from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Perfil, Materia, Atividade, Meta, Configuracao


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'seu.email@exemplo.com',
            'required': True,
        })
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'required': True,
        })
    )


class CadastroForm(UserCreationForm):
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'seu.email@exemplo.com',
            'required': True,
        })
    )
    first_name = forms.CharField(
        label='Nome Completo',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Seu nome completo',
            'required': True,
        })
    )
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Minimo 8 caracteres',
            'required': True,
        })
    )
    password2 = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Digite novamente',
            'required': True,
        })
    )
    objetivo = forms.ChoiceField(
        label='Objetivo Principal',
        choices=Perfil.OBJETIVO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-input'}),
        required=False
    )

    class Meta:
        model = User
        fields = ['first_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['telefone', 'data_nascimento', 'instituicao', 'serie', 'objetivo']
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '(00) 00000-0000'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'instituicao': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Colegio Estadual...'}),
            'serie': forms.Select(attrs={'class': 'form-input'}),
            'objetivo': forms.Select(attrs={'class': 'form-input'}),
        }


class MateriaForm(forms.ModelForm):
    class Meta:
        model = Materia
        fields = ['nome', 'professor', 'topicos', 'carga_horaria', 'prioridade', 'progresso']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Matematica'}),
            'professor': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Carlos Silva'}),
            'topicos': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Ex: Algebra, Geometria...', 'rows': 3}),
            'carga_horaria': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '6', 'min': 1}),
            'prioridade': forms.Select(attrs={'class': 'form-input'}),
            'progresso': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '50', 'min': 0, 'max': 100}),
        }

    def clean_progresso(self):
        valor = self.cleaned_data.get('progresso')
        if valor is not None and not 0 <= valor <= 100:
            raise forms.ValidationError('O progresso deve estar entre 0 e 100.')
        return valor

    def clean_carga_horaria(self):
        valor = self.cleaned_data.get('carga_horaria')
        if valor is not None and not 1 <= valor <= 168:
            raise forms.ValidationError('A carga horária semanal deve estar entre 1 e 168 horas.')
        return valor


class AtividadeForm(forms.ModelForm):
    class Meta:
        model = Atividade
        fields = ['titulo', 'materia', 'dia_semana', 'hora_inicio', 'hora_fim']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Revisao de Algebra'}),
            'materia': forms.Select(attrs={'class': 'form-input'}),
            'dia_semana': forms.Select(attrs={'class': 'form-input'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
        }

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get('hora_inicio'), dados.get('hora_fim')
        if inicio and fim and fim <= inicio:
            self.add_error('hora_fim', 'O horário de término deve ser depois do início.')
        return dados


class MetaForm(forms.ModelForm):
    class Meta:
        model = Meta
        fields = ['titulo', 'materia', 'descricao', 'meta_progresso', 'progresso_atual', 'prazo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Matematica - ENEM'}),
            'materia': forms.Select(attrs={'class': 'form-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Descreva os objetivos...', 'rows': 3}),
            'meta_progresso': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '80', 'min': 1, 'max': 100}),
            'progresso_atual': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '50', 'min': 0, 'max': 100}),
            'prazo': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }

    def clean(self):
        dados = super().clean()
        alvo, atual = dados.get('meta_progresso'), dados.get('progresso_atual')
        if alvo is not None and not 1 <= alvo <= 100:
            self.add_error('meta_progresso', 'A meta deve estar entre 1 e 100.')
        if atual is not None and not 0 <= atual <= 100:
            self.add_error('progresso_atual', 'O progresso atual deve estar entre 0 e 100.')
        return dados


class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        exclude = ['usuario']