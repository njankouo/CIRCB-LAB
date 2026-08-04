# mon_app/templatetags/role_tags.py
from django import template

register = template.Library()

@register.filter(name='has_role')
def has_role(user, role_code):
    """Vérifie si l'utilisateur connecté possède un rôle spécifique par son code."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.roles.filter(role__code=role_code).exists()