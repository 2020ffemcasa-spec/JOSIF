from .models import Perfil

def user_context(request):
    """Context processor para dados do usuário em todas as páginas"""
    context = {}
    
    if request.user.is_authenticated:
        try:
            perfil = Perfil.objects.get(usuario=request.user)
            context['perfil'] = perfil
            context['user_initials'] = perfil.get_iniciais()
        except Perfil.DoesNotExist:
            context['perfil'] = None
            context['user_initials'] = request.user.username[:2].upper()
    
    return context