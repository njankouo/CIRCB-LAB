from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(role_codes):
    """
    Décorateur pour restreindre l'accès selon les codes de rôle personnalisés.
    Accepte un code unique (str) ou une liste de codes (list).
    """
    if isinstance(role_codes, str):
        role_codes = [role_codes]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            # Les superutilisateurs ont accès à tout
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Vérifie si l'utilisateur possède au moins un des rôles via la relation 'roles'
            has_role = request.user.roles.filter(role__code__in=role_codes).exists()
            
            if not has_role:
                raise PermissionDenied("Vous n'avez pas l'autorisation d'accéder à ce module.")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator