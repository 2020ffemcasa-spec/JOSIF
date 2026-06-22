from django.shortcuts import redirect
from django.contrib import messages
from .models import Perfil

def user_has_profile(view_func):
    """Decorator para verificar se o usuário tem perfil"""
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                perfil = Perfil.objects.get(usuario=request.user)
            except Perfil.DoesNotExist:
                messages.warning(request, 'Complete seu perfil para continuar.')
                return redirect('configuracoes')
        return view_func(request, *args, **kwargs)
    return wrapper