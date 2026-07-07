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
urlpatterns = [
    
    path('', views.connexion_view, name='connexion'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('personnel/', views.personnel, name='personnel'),
    path('authentification/', views.authentification, name='authentification'),
    path('logout/', views.logout_view, name='logout'),
    path('dossiers/patients/', views.dossiers_patients, name='dossiers_patients'),
    path('configurations/', views.configurations, name='configurations'),
    path('fiches-echantillons/', views.fiches_echantillons, name='fiches_echantillons'),
    path('echantillons/', views.echantillons, name='echantillons'),
    
    path('structures/', views.structures, name='structures'),
    
    path('add_level/', views.add_level, name='add_level'),
    path('add_sub_structure/', views.add_sub_structure, name='add_sub_structure'),
    path('admin/', admin.site.urls),
    path('search_district/<int:region_id>/', views.search_district, name='search_district'),
    path('search_fosa/<int:district_id>/', views.search_fosa, name='search_fosa'),
    path('search_contact/<int:contact_id>/', views.search_contact, name='search_contact'),
    path('enregistrer_fiche_echantillon/', views.enregistrer_fiche_echantillon, name='enregistrer_fiche_echantillon'),
    path('details-fiche/<str:slug>/', views.details_fiche, name='details-fiche')
   
]
    

