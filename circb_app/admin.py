from django.contrib import admin
from .models import *




# ==========================================
# 1. GESTION DES RÔLES ET UTILISATEURS
# ==========================================


# Optionnel : Si vous souhaitez intégrer les rôles directement dans la modification des utilisateurs Django
# (Décommentez les 4 lignes ci-dessous si vous voulez remplacer l'admin User par défaut)
# admin.site.unregister(User)
# @admin.register(User)
# class CustomUserAdmin(BaseUserAdmin):
#     inlines = [RoleUserInline]

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'description')
    search_fields = ('nom', 'code')
    list_filter = ('nom',)

@admin.register(RoleUser)
class RoleUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role', 'user')
    search_fields = ('user__username', 'user__email', 'role__nom')


# ==========================================
# 2. CONFIGURATION DYNAMIQUE DES ACCÈS (RÔLES <-> URLS)
# ==========================================

@admin.register(Transporteur)
class TransporteurAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'tel', 'email')
    search_fields = ('code', 'nom', 'email')

@admin.register(MoyenTransport)
class MoyenTransportAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom')
    search_fields = ('code', 'nom')

@admin.register(Structure_Hierachy)
class StructureHierachyAdmin(admin.ModelAdmin):
    list_display = ('nom', 'rang', 'is_active')
    list_filter = ('is_active', 'rang')
    search_fields = ('nom',)
    ordering = ('rang',)

@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ('nom', 'designation', 'hierachy', 'parent', 'date_creation')
    list_filter = ('hierachy', 'date_creation')
    search_fields = ('nom', 'designation')
    autocomplete_fields = ('parent',)  # Permet une recherche dynamique si la liste est longue

    # Permet à Django Admin d'utiliser le champ 'nom' pour la recherche dans l'autocomplete
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct

@admin.register(FicheEchantillon)
class FicheEchantillonAdmin(admin.ModelAdmin):
    # Les champs existent à nouveau, vous pouvez les inclure ici
    raw_id_fields = ('fosa', 'district', 'region', 'moyen_transport') 
    
    list_display = ('code', 'fosa', 'district', 'region', 'date_reception', 'status')
    
    # Filtres standards directs
    list_filter = (
        'status',
        'moyen_transport',
        'region',
        'district',
        'fosa',
    )
    
    search_fields = ('code', 'fosa__nom', 'transporteur', 'expediteur')


@admin.register(PorteEntree)
class PorteEntreeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code')
    search_fields = ('nom', 'code')
    list_per_page = 20

@admin.register(ProfilaxieArv)
class ProfilaxieArvAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code')
    search_fields = ('nom', 'code')
    list_per_page = 20

@admin.register(ModeAllaitement)
class ModeAllaitementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code')
    search_fields = ('nom', 'code')
    list_per_page = 20

@admin.register(ModeAccouchement)
class ModeAccouchementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code')
    search_fields = ('nom', 'code')
    list_per_page = 20

@admin.register(ProtocolePTME)
class ProtocolePTMEAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code')
    search_fields = ('nom', 'code')
    list_per_page = 20



@admin.register(RaisonPrelevement)
class RaisonPrelevementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code')
    search_fields = ('nom', 'code')
    list_per_page = 20

@admin.register(ResultatPcr)
class ResultatPcrAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code')
    search_fields = ('nom', 'code')
    list_per_page = 20

@admin.register(Echantillon)
class EchantillonAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'code_circb',
        'fiche',
        'get_resultat_pcr', # Fonction personnalisée
        'date_prelevement',
    )

    @admin.display(description='Résultat PCR')
    def get_resultat_pcr(self, obj):
        if obj.resultat_pcr:
            return obj.resultat_pcr
        return "Non renseigné"

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "nom")
    search_fields = ("code", "nom")