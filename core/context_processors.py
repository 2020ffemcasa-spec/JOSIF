from .models import Configuracao

def user_context(request):
    """Context processor para dados do usuário"""
    context = {}

    if request.user.is_authenticated:
        config, created = Configuracao.objects.get_or_create(usuario=request.user)
        context['config'] = config

    return context
