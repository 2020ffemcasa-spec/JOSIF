from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Perfil, Materia, Atividade, Meta, Configuracao

class CustomAuthenticationForm(AuthenticationForm):
    """Formulário de login personalizado"""
    
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
    
    error_messages = {
        'invalid_login': 'E-mail ou senha inválidos.',
        'inactive': 'Esta conta está inativa.',
    }


class CadastroForm(UserCreationForm):
    """Formulário de cadastro de usuário"""
    
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
            'placeholder': 'Mínimo 8 caracteres',
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
        widget=forms.Select(attrs={
            'class': 'form-input',
        }),
        required=False
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'email', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email


class PerfilForm(forms.ModelForm):
    """Formulário de perfil"""
    
    class Meta:
        model = Perfil
        fields = ['telefone', 'data_nascimento', 'instituicao', 'serie', 'objetivo']
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '(00) 00000-0000'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'instituicao': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Colégio Estadual...'}),
            'serie': forms.Select(attrs={'class': 'form-input'}),
            'objetivo': forms.Select(attrs={'class': 'form-input'}),
        }


class MateriaForm(forms.ModelForm):
    """Formulário de matéria"""
    
    class Meta:
        model = Materia
        fields = ['nome', 'professor', 'topicos', 'carga_horaria', 'prioridade', 'progresso']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Matemática'}),
            'professor': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Carlos Silva'}),
            'topicos': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Ex: Álgebra, Geometria...', 'rows': 3}),
            'carga_horaria': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '6', 'min': 1}),
            'prioridade': forms.Select(attrs={'class': 'form-input'}),
            'progresso': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '50', 'min': 0, 'max': 100}),
        }


class AtividadeForm(forms.ModelForm):
    """Formulário de atividade"""
    
    class Meta:
        model = Atividade
        fields = ['titulo', 'materia', 'dia_semana', 'hora_inicio', 'hora_fim']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Revisão de Álgebra'}),
            'materia': forms.Select(attrs={'class': 'form-input'}),
            'dia_semana': forms.Select(attrs={'class': 'form-input'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
        }


class MetaForm(forms.ModelForm):
    """Formulário de meta"""
    
    class Meta:
        model = Meta
        fields = ['titulo', 'materia', 'descricao', 'meta_progresso', 'progresso_atual', 'prazo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Matemática - ENEM'}),
            'materia': forms.Select(attrs={'class': 'form-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Descreva os objetivos...', 'rows': 3}),
            'meta_progresso': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '80', 'min': 1, 'max': 100}),
            'progresso_atual': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '50', 'min': 0, 'max': 100}),
            'prazo': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }


class ConfiguracaoForm(forms.ModelForm):
    """Formulário de configuração"""
    
    class Meta:
        model = Configuracao
        exclude = ['usuario']
        widgets = {
            'horario_lembrete': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
        }