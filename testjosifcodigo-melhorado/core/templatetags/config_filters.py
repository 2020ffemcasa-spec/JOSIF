from django import template

register = template.Library()

@register.filter
def get_cor(value):
    """Retorna a cor com fallback seguro"""
    if value:
        return value
    return '#2878FF'