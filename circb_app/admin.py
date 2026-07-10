from django.contrib import admin
from .models import *

@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'mail', 'tel', 'sexe', 'bd_user')
    search_fields = ('nom', 'prenom', 'mail', 'tel')
    list_filter = ('sexe',)
    ordering = ('nom',)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom')
    search_fields = ('code', 'nom')

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
    list_display = ('code', 'region', 'district', 'fosa', 'transporteur', 'nombre_echantillon', 'date_reception')
    list_filter = ('date_reception', 'date_expedition', 'region', 'district')
    search_fields = ('code', 'observation', 'transporteur__nom', 'receptioniste__nom')
    date_hierarchy = 'date_reception'  # Ajoute une barre de navigation temporelle très pratique en haut
    raw_id_fields = ('region', 'district', 'fosa')  # Évite de charger des milliers de structures dans un select classique


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

