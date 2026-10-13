from .models import Configuracao, Perfil


def user_context(request):
    """Disponibiliza `config` e `perfil` do usuário logado em todos os templates.

    O `perfil` é necessário para a sidebar (base.html) mostrar o avatar em todas as
    páginas — antes ele só existia na tela de Configurações.
    """
    context = {}

    if request.user.is_authenticated:
        config, _ = Configuracao.objects.get_or_create(usuario=request.user)
        perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
        context['config'] = config
        context['perfil'] = perfil

    return context
