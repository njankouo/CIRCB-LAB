"""
URL configuration for circb_projet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views
from django.urls import path, include
urlpatterns = [
    path('', include('pwa.urls')),
    path('', views.connexion_view, name='connexion'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('personnel/', views.personnel, name='personnel'),
    path('authentification/', views.authentification, name='authentification'),
    path('logout/', views.logout_view, name='logout'),
    path('dossiers/patients/', views.dossiers_patients, name='dossiers_patients'),
    path('configurations/', views.configurations, name='configurations'),
    path('fiches-echantillons/', views.fiches_echantillons, name='fiches_echantillons'),
    path('saisir-echantillon/<int:id>/', views.echantillons, name='saisir-echantillon'),
    
    path('structures/', views.structures, name='structures'),
    
    path('add_level/', views.add_level, name='add_level'),
    path('add_sub_structure/', views.add_sub_structure, name='add_sub_structure'),
    path('admin/', admin.site.urls),
    path('search_district/<int:region_id>/', views.search_district, name='search_district'),
    path('search_fosa/<int:district_id>/', views.search_fosa, name='search_fosa'),
    path('search_contact/<int:contact_id>/', views.search_contact, name='search_contact'),
    path('enregistrer_fiche_echantillon/', views.enregistrer_fiche_echantillon, name='enregistrer_fiche_echantillon'),
    path('details-fiche/<str:slug>/', views.details_fiche, name='details-fiche'),
    path('search_porte_entree/<int:porte_entree_id>/', views.search_porte_entree, name='search_porte_entree'),
    path('verifier_patient/', views.verifier_patient, name='verifier_patient'),
    path('create_patient/', views.creer_patient, name='create_patient'),
    path('details-patient/<str:slug>/', views.details_patient, name='details-patient'),
    
    path('echantillonages/', views.echantillonages, name='echantillonages'),
    
    path('create_or_edit_role/', views.create_or_edit_role, name='create_or_edit_role'),
    path('delete_role/<int:role_id>/', views.delete_role, name='delete_role'),
    path('edit_role/<int:role_id>/', views.edit_role, name='edit_role'),
    
    path('ajouter_echantillon/', views.ajouter_echantillon, name='ajouter_echantillon'),
    
    path('detail-fiche/<str:code>/', views.detail_fiche, name='detail-fiche'),
    path('fiche-echantillon/<slug:slug>/', views.fiche_echantillon, name='fiche-echantillon'),
    
    path('resultats-test/', views.resultats_test, name='resultats-test'),
    
    path('enregistrer_resultat_ajax/', views.enregistrer_resultat_ajax, name='enregistrer_resultat_ajax'),
    
    path('resultats/', views.resultats, name='resultats'),
    
    path('imprimer_resultat_pdf/<int:resultat_id>/', views.imprimer_resultat_pdf,name='imprimer_resultat_pdf'),
    
    path('bordeaux-sortie/', views.bordeaux_sortie, name='bordeaux-sortie'),
    
    path('supprimer-fiche/<int:id>/', views.supprimer_fiche, name='supprimer-fiche'),
    
    path('fiches/', views.fiches, name='fiches'),
    
    path('verification-code/<str:code>/', views.verification_code, name='verification-code'),
    
    path('rechercher-patient/', views.rechercher_patient, name='rechercher_patient'),
    
    path('search_fosas/<int:district_id>/', views.search_fosas, name='search_fosas'),
    
    path('search_districts/<int:region_id>/', views.search_districts, name='search_districts'),
    
    path('delete-role/<int:id>/', views.delete_role, name='delete-role'),
    
    path('save-personnel/', views.save_personnel, name='save-personnel'),
    
    path('recherche-patient/', views.recherche_patient, name='recherche-patient'),
    
    path('profile/', views.profile, name='profile')
  
   
]
    

handler404 = 'circb_app.views.custom_page_not_found_view'
handler500 = 'circb_app.views.custom_error_view'