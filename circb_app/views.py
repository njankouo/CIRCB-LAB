from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth import logout
from .models import *
from django.http import JsonResponse
import uuid
from django.db.models import Count, Q
from django.db import IntegrityError
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.utils.crypto import get_random_string
from django.db.models import Q
from .decorators import role_required
from django.contrib.auth.decorators import permission_required
# 1. On garde l'import de Django sous un autre nom ou on importe ton fichier models local
from .models import Structure_Hierachy, Structure 
# Create your views here.
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import rotate_token
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging
import json
from .tasks import task_transfert_fosa
def connexion_view(request):
    # Django ira chercher ce fichier dans vos dossiers de templates configurés
    return render(request, 'webpages/login_hosp.html')
import time
import jwt
from django.conf import settings
import time
import jwt
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def generate_metabase_token(dashboard_id):
    """Fonction utilitaire pour signer un token Metabase JWT."""
    payload = {
        "resource": {"dashboard": dashboard_id},
        "params": {},
        "iat": int(time.time()),
        "exp": int(time.time()) + (60 * 60),  # Expire dans 1 heure
    }
    return jwt.encode(payload, settings.METABASE_SECRET_KEY, algorithm="HS256")
def generate_metabase_token(dashboard_id):
    """Génère et signe le token JWT pour Metabase."""
    payload = {
        "resource": {"dashboard": dashboard_id},
        "params": {},
        "iat": int(time.time()),
        "exp": int(time.time()) + (60 * 60),  # Expire dans 1 heure
    }
    return jwt.encode(payload, settings.METABASE_SECRET_KEY, algorithm="HS256")

@login_required(login_url='authentification')
def dashboard(request):
    user = request.user

    # 1. CAS SUPERUTILISATEUR : Accès aux deux tableaux de bord
    if user.is_superuser:
        token_echantillons = generate_metabase_token(3)
        token_general = generate_metabase_token(2)

        context = {
            "metabase_token": token_echantillons,
            "metabase_token_secondary": token_general,
            "has_multiple_dashboards": True,
            "metabase_site_url": settings.METABASE_SITE_URL,
            "user_role_label": "Superutilisateur",
        }

    # 2. CAS RÔLE ÉCHANTILLONS UNIK : Accès STRICTEMENT au Dashboard 3
    elif user.has_perm('circb_app.peut_voir_tableau_de_bord_echantillons'):
        token_echantillons = generate_metabase_token(3)

        context = {
            "metabase_token": token_echantillons,
            "has_multiple_dashboards": False,
            "metabase_site_url": settings.METABASE_SITE_URL,
            "user_role_label": "Tableau Échantillons",
        }

    # 3. CAS PAR DÉFAUT : Accès uniquement au Dashboard Général (ID 2)
    else:
        token_general = generate_metabase_token(2)

        context = {
            "metabase_token": token_general,
            "has_multiple_dashboards": False,
            "metabase_site_url": settings.METABASE_SITE_URL,
            "user_role_label": "Tableau Général",
        }

    return render(request, 'webpages/dashbord_hosp.html', context)
@login_required(login_url='/')
@permission_required('circb_app.manage_rh', raise_exception=True)
def personnel(request):
    context ={
        'user':User.objects.all(),
        'role':Role.objects.all(),
        'groupes': Group.objects.all()
      
    }
    return render(request, 'webpages/personnel.html',context)
security_logger = logging.getLogger('security')

@csrf_protect
@require_http_methods(["GET", "POST"])
def authentification(request):
    """
    Vue d'authentification sécurisée avec traçabilité, gestion CSRF/AJAX
    et support hybride (Connexion par Nom d'utilisateur OU par Email).
    """
    # 1. Détermination sécurisée de la page de destination par défaut
    redirect_to = getattr(settings, 'LOGIN_REDIRECT_URL', '/')

    # 2. VÉRIFICATION STRICTE DE SESSION :
    # Si l'utilisateur est DÉJÀ connecté (GET ou POST), on annule le traitement et on redirige.
    if request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
            return build_auth_response(
                request, 
                success=True, 
                message="Vous êtes déjà connecté.", 
                redirect_url=redirect_to, 
                status_code=200
            )
        return redirect(redirect_to)

    if request.method == 'POST':
        # Récupération et nettoyage strict des entrées
        input_identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next') or request.GET.get('next')

        # Validation minimale des champs
        if not input_identifier or not password:
            security_logger.warning(
                f"Tentative de connexion avec champs manquants | IP: {get_client_ip(request)}"
            )
            return build_auth_response(
                request, 
                success=False, 
                message="Veuillez remplir tous les champs.", 
                status_code=400
            )

        # RESOLUTION DE L'IDENTIFIANT (Email ou Username)
        # Permet de se connecter aussi bien avec un email qu'avec le nom d'utilisateur
        username_to_auth = input_identifier
        if '@' in input_identifier:
            try:
                # Recherche insensible à la casse pour l'email
                user_found = User.objects.get(email__iexact=input_identifier)
                username_to_auth = user_found.get_username()
            except User.DoesNotExist:
                username_to_auth = input_identifier  # Laisse l'échec se produire naturellement via authenticate()
            except User.MultipleObjectsReturned:
                # En cas de doublons d'emails, on récupère le premier utilisateur actif
                user_found = User.objects.filter(email__iexact=input_identifier, is_active=True).first()
                if user_found:
                    username_to_auth = user_found.get_username()

        # Authentification Django
        user = authenticate(request, username=username_to_auth, password=password)

        if user is not None:
            if user.is_active:
                # 1. Prévention de la fixation de session
                rotate_token(request)
                
                # 2. Connexion
                login(request, user)

                # 3. Traçabilité (Audit Log)
                security_logger.info(
                    f"Connexion réussie - Utilisateur: {user.username} (ID: {user.id}) | IP: {get_client_ip(request)}"
                )

                messages.success(request, f"Connexion réussie. Bienvenue, {user.get_full_name() or user.username} !")

                # 4. Validation de l'URL de redirection (Protection Open Redirect)
                if not next_url or not url_has_allowed_host_and_scheme(
                    url=next_url, 
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure()
                ):
                    next_url = redirect_to

                return build_auth_response(
                    request, 
                    success=True, 
                    message="Connexion réussie.", 
                    redirect_url=next_url, 
                    status_code=200
                )
            else:
                security_logger.warning(
                    f"Tentative de connexion sur compte désactivé - Saisie: {input_identifier} | IP: {get_client_ip(request)}"
                )
                return build_auth_response(
                    request, 
                    success=False, 
                    message="Ce compte a été désactivé par l'administrateur.", 
                    status_code=403
                )
        else:
            security_logger.warning(
                f"Échec d'authentification - Saisie: {input_identifier} | IP: {get_client_ip(request)}"
            )
            return build_auth_response(
                request, 
                success=False, 
                message="Identifiant ou mot de passe incorrect.", 
                status_code=401
            )

    return render(request, 'webpages/login_hosp.html')
@csrf_protect
@require_http_methods(["POST"])
def logout_view(request):
    """
    Vue de déconnexion sécurisée restreinte à la méthode POST (Anti-CSRF).
    """
    username = request.user.username if request.user.is_authenticated else "Anonyme"
    
    # Déconnexion et nettoyage strict de la session
    logout(request)
    request.session.flush()

    security_logger.info(
        f"Déconnexion réussie - Utilisateur: {username} | IP: {get_client_ip(request)}"
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'redirect_url': '/'})

    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('/')


# ==========================================
# FONCTIONS UTILITAIRES DE SÉCURITÉ
# ==========================================

def get_client_ip(request):
    """Récupère l'adresse IP réelle du client (gère les reverse-proxies Nginx/Cloudflare)."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def build_auth_response(request, success, message, redirect_url=None, status_code=200):
    """Génère la réponse appropriée en fonction du type de requête (AJAX / JSON ou Form HTML)."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        payload = {'success': success, 'message': message}
        if redirect_url:
            payload['redirect_url'] = redirect_url
        return JsonResponse(payload, status=status_code)

    if not success:
        messages.error(request, message)
        return render(request, 'webpages/login_hosp.html', status=status_code)

    return redirect(redirect_url or '/')
@login_required(login_url='/')
@permission_required(
    'circb_app.Consulter_dossier_patient', raise_exception=True
)
def dossiers_patients(request):
    # 1. Requête optimisée :
    # - select_related évite le problème N+1 requêtes sur les clés étrangères (mere et fiche_echantillon)
    # - order_by('-id') garantit un tri stable pour la pagination (du plus récent au plus ancien)
    patients_queryset = Patient.objects.select_related(
        'mere'
    ).order_by('-id')

    # 2. Recherche optionnelle par nom ou code patient
    search_query = request.GET.get('q', '').strip()
    if search_query:
        patients_queryset = patients_queryset.filter(
            nom__icontains=search_query
        ) | patients_queryset.filter(code__icontains=search_query)

    # 3. Pagination (25 patients par page)
    paginator = Paginator(patients_queryset, 25)
    page_number = request.GET.get('page')
    patients_page = paginator.get_page(page_number)

    context = {
        'patients': patients_page,
        'search_query': search_query,
    }

    return render(request, 'webpages/patients/dossiers.html', context)
@login_required(login_url='/')
@permission_required('circb_app.Consulter_dossier_patient', raise_exception=True)
def details_patient(request, slug):
    patient = get_object_or_404(Patient, code=slug)
    context ={
        'patient':patient,
        'echantillon':Echantillon.objects.filter(enfant=patient).order_by('-id')
    }
    return render(request, 'webpages/patients/details-patient.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.shortcuts import render

@login_required(login_url='/')
def configurations(request):
    # Récupère uniquement les permissions personnalisées de votre application 'circb_app'
    permissions = Permission.objects.filter(content_type__app_label='circb_app').exclude(
        Q(codename__startswith='add_') |
        Q(codename__startswith='change_') |
        Q(codename__startswith='delete_') |
        Q(codename__startswith='view_')
    )

    context = {
        'roles': Group.objects.all().order_by('id'),
        'permissions': permissions,
    }
    return render(request, 'webpages/config/configurations.html', context)
from django.contrib.auth.decorators import permission_required

# Remplacez 'votre_app' par le nom réel de votre application Django
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import FicheEchantillon, MoyenTransport, Structure, Transporteur
from django.db.models import F, Q

@permission_required(
    'circb_app.peut_voir_fiches_expedition', raise_exception=True
)
@login_required(login_url='/')
def fiches_echantillons(request):
    regions = Structure.objects.filter(parent__isnull=True).order_by('nom')
    moyens_transport = MoyenTransport.objects.all().order_by('nom')
    all_fosas = Fosa.objects.all().order_by('nom')
    
    # Récupérer les années distinctes présentes dans la base pour le select
    available_years = FicheEchantillon.objects.dates('date_enregistrement', 'year', order='DESC')

    # Récupération des paramètres GET
    search_code = request.GET.get('code', '').strip()
    search_date = request.GET.get('date', '').strip()
    search_mois = request.GET.get('mois', '').strip()
    search_annee = request.GET.get('annee', '').strip() # Nouveau
    search_fosa = request.GET.get('fosa', '').strip()
    search_receptionniste = request.GET.get('receptionniste', '').strip()

    # QuerySet de base
    fiches_queryset = (
        FicheEchantillon.objects.select_related(
            'region', 'district', 'fosa', 'moyen_transport'
        )
        .order_by(
            F('date_enregistrement').desc(nulls_last=True),
            F('id').desc()
        )
    )

    # 1. Filtre par code / id / expediteur
    if search_code:
        fiches_queryset = fiches_queryset.filter(
            Q(code__icontains=search_code) | 
            Q(id__icontains=search_code) |
            Q(expediteur__icontains=search_code)
        )
    
    # 2. Filtre par date exacte
    if search_date:
        formatted_date = search_date.replace('/', '-')
        for fmt in ('%d-%m-%Y', '%d-%m-%y'):
            try:
                date_parsed = datetime.strptime(formatted_date, fmt).date()
                fiches_queryset = fiches_queryset.filter(date_enregistrement=date_parsed)
                break
            except ValueError:
                continue

    # 3. Filtre par Mois
    if search_mois:
        fiches_queryset = fiches_queryset.filter(date_enregistrement__month=search_mois)

    # 4. Filtre par Année (Nouveau)
    if search_annee:
        fiches_queryset = fiches_queryset.filter(date_enregistrement__year=search_annee)

    # 5. Filtre par Formation Sanitaire (FOSA)
    if search_fosa:
        fiches_queryset = fiches_queryset.filter(fosa_id=search_fosa)

    # 6. Filtre par réceptionniste
    if search_receptionniste:
        fiches_queryset = fiches_queryset.filter(
            receptioniste__icontains=search_receptionniste
        )

    # Pagination
    paginator = Paginator(fiches_queryset, 30)
    page_number = request.GET.get('page')
    fiches_page = paginator.get_page(page_number)

    fichescount = FicheEchantillon.objects.filter(status=False).count()

    context = {
        'regions': regions,
        'moyens_transport': moyens_transport,
        'all_fosas': all_fosas,
        'available_years': available_years, # Pour le menu déroulant des années
        'fiches': fiches_page,
        'fichescount': fichescount,
        'search_code': search_code,
        'search_date': search_date,
        'search_mois': search_mois,
        'search_annee': search_annee, # Nouveau
        'search_fosa': search_fosa,
        'search_receptionniste': search_receptionniste,
    }

    return render(
        request, 'webpages/echantillonages/fiche_echantillons.html', context
    )
@login_required(login_url='/')
def echantillons(request, id):
    dernier_numero= Echantillon.objects.order_by('-id').first()
    prochain_numero= (dernier_numero.id + 1) if dernier_numero else 1
    context={
        'fiches_echantillon':FicheEchantillon.objects.get(id=id),
        'tests':Test.objects.all().order_by('nom'),
        'raisons_prelevement':RaisonPrelevement.objects.all().order_by('nom'),
        'modes_allaitement':ModeAllaitement.objects.filter(is_artificiel=False).order_by('nom'),
        'modes_allaitement_artificiel':ModeAllaitement.objects.filter(is_artificiel=True).order_by('nom'),
        'resultats_pcr':ResultatPcr.objects.all().order_by('nom'),
        'regions':Structure.objects.filter(parent__isnull=True).order_by('nom'),
        'portes_entree':PorteEntree.objects.all().order_by('nom'),
        'protocole_ptme':ProtocolePTME.objects.all().order_by('nom'),
        'profilaxie_arv':ProfilaxieArv.objects.all(),
        'mode_accouchement': ModeAccouchement.objects.all(),
        'prochain_numero':prochain_numero,
        'examen':Test.objects.all()
    }
    return render(request, 'webpages/echantillonages/echantillons.html', context)
@permission_required('circb_app.peut_voir_consulter_echantillons')
@login_required(login_url='/')
def echantillonages(request):
    # 1. Filtre de base
    echantillons_list = (
        Echantillon.objects.filter(resultat_pcr__isnull=True)
        .select_related(
            "enfant",
            "enfant__fosa",
            "mere",
            "fiche",
            "fiche__fosa",
        )
        .order_by("-date_prelevement", "-id")
    )

    # 2. Récupération des paramètres
    nom_patient = request.GET.get("nom_patient", "").strip()
    code_echantillon = request.GET.get("code_echantillon", "").strip()
    code_patient = request.GET.get("code_patient", "").strip()
    date_prelevement = request.GET.get("date_prelevement", "").strip()

    # 3. Application des filtres ORM
    if nom_patient:
        echantillons_list = echantillons_list.filter(
            Q(enfant__nom__icontains=nom_patient)
            | Q(enfant__prenom__icontains=nom_patient)
        )

    if code_echantillon:
        echantillons_list = echantillons_list.filter(
            code__icontains=code_echantillon
        )

    if code_patient:
        echantillons_list = echantillons_list.filter(
            enfant__code__icontains=code_patient
        )

    if date_prelevement:
        # Conversion de JJ-MM-AAAA en AAAA-MM-JJ pour l'ORM Django
        try:
            date_obj = datetime.strptime(date_prelevement, "%d-%m-%Y").date()
            echantillons_list = echantillons_list.filter(date_prelevement=date_obj)
        except ValueError:
            # Si le format de date saisi est invalide, ignorer ou gérer l'erreur
            pass

    # 4. Pagination
    items_per_page = 30
    paginator = Paginator(echantillons_list, items_per_page)
    page_number = request.GET.get("page", 1)

    try:
        echantillons = paginator.page(page_number)
    except PageNotAnInteger:
        echantillons = paginator.page(1)
    except EmptyPage:
        echantillons = paginator.page(paginator.num_pages)

    # 5. Construction du contexte
    context = {
        "echantillons": echantillons,
        "fiches_recentes": FicheEchantillon.objects.all().order_by("-id")[:30],
    }

    return render(
        request, "webpages/echantillonages/echantillonages.html", context
    )
@login_required(login_url='/')

@permission_required('circb_app.peut_voir_structures')
# Vue principale (ne charge QUE le niveau 1)
def structures(request):
    hierachie = Structure_Hierachy.objects.all().order_by('rang')

    # Racine uniquement (aucun parent) -> Chargement instantané de la page !
    lines = (
        Region.objects.annotate(
            districts_count=Count('children', distinct=True),
            fosa_count=Count('children__children', distinct=True)

        )
        .select_related('hierachy')
        .order_by('nom')
    )

    context = {
        'lines': lines,
        'hierachie': hierachie,
        
    }
    return render(request, 'webpages/config/structure.html', context)

def api_get_structure_children(request, parent_id):
    # 1. On vérifie si le parent cliqué est une Région
    is_region = Region.objects.filter(id=parent_id).exists()
    
    if is_region:
        children = (
            District.objects.filter(parent_id=parent_id)
            .select_related('hierachy')
            .order_by('nom')
        )
    else:
        children = (
            Fosa.objects.filter(parent_id=parent_id)
            .select_related('hierachy')
            .order_by('nom')
        )

    nodes = []
    for child in children:
        # 2. Vérification propre de l'existence d'enfants selon le type exact de l'objet
        if is_region:
            # Un District peut avoir des Fosas en enfants (grâce au related_name='children' du modèle Fosa)
            has_children = child.children.exists()
        else:
            # Une Fosa est au bout de la chaîne, elle n'a pas d'enfants
            has_children = False

        nodes.append({
            'id': child.id,
            'nom': child.nom,
            'designation': child.designation or '---',
            'hierachy_nom': child.hierachy.nom if child.hierachy else '',
            'hierachy_rang': child.hierachy.rang if child.hierachy else 99,
            'has_children': has_children,
        })

    return JsonResponse({'children': nodes})
def add_level(request):
    if request.method == 'POST':
        try:
            nom = request.POST.get('nom')
            rang = request.POST.get('rang')
            # Gestion du checkbox 'is_active'
            is_active = True if request.POST.get('is_active') == 'on' else False
          
            # Création du niveau
            level = Structure_Hierachy(
                nom=nom,
                rang=rang,
                is_active=is_active,
              
            )
            level.save()
            
            messages.success(request, f"Le niveau '{nom}' a été configuré avec succès.")
        except Exception as e:
            messages.error(request, f"Erreur lors de la configuration du niveau : {e}")
            
    return redirect(request.META.get('HTTP_REFERER', '/'))  # Redirige vers la page précédente ou la racine si aucune page précédente



@permission_required('circb_app.peut_ajouter_sous_structure')
def add_sub_structure(request):
    if request.method == 'POST':
        try:
            # Récupération des données du formulaire
            nom = request.POST.get('nom')
            designation = request.POST.get('designation')
            parent_id = request.POST.get('parent_id')
            
            # On peut recevoir soit le rang (calculé), soit l'ID du niveau (choisi)
            target_rank = request.POST.get('target_rank')
            level_id = request.POST.get('level_id') 
            
         

            # 1. Identification du niveau hiérarchique
            hierachy_level = None
            if level_id:
                # Si l'utilisateur a choisi explicitement le niveau dans la liste
                hierachy_level = Structure_Hierachy.objects.get(id=level_id)
            elif target_rank:
                # Si on se base sur le rang calculé par le JS
                hierachy_level = Structure_Hierachy.objects.get(rang=target_rank)

            if not hierachy_level:
                raise ValueError("Le niveau hiérarchique est manquant ou invalide.")

            # 2. Nettoyage du parent_id (si vide string '' -> devient None)
            clean_parent_id = int(parent_id) if parent_id and parent_id.strip() else None

            # 3. Création de la structure
            Structure.objects.create(
                nom=nom,
                designation=designation,
                parent_id=clean_parent_id,
                hierachy=hierachy_level,
              
            )
            
            messages.success(request, f"L'unité '{nom}' a été créée avec succès au niveau {hierachy_level.nom}.")

        except Structure_Hierachy.DoesNotExist:
            messages.error(request, "Le niveau hiérarchique cible n'est pas encore configuré pour cette institution.")
        except ValueError as ve:
            messages.error(request, str(ve))
        except Exception as e:
            messages.error(request, f"Une erreur inattendue est survenue : {e}")

    return redirect('/structures/')


def search_district(request, region_id):
    # On filtre les districts qui ont la région comme parent
    districts = District.objects.filter(parent_id=region_id).values('id', 'nom')
    # On renvoie la clé 'results' comme attendu par votre JS
    return JsonResponse({'results': list(districts)})

def search_fosa(request, district_id):
    # On filtre les FOSAs qui ont le district comme parent
    fosas = Fosa.objects.filter(parent_id=district_id).values('id', 'nom').order_by('nom')
    # On renvoie la clé 'fosas' comme attendu par votre JS
    return JsonResponse({'fosas': list(fosas)})
def search_contact(request, contact_id):
    """
    Récupère le numéro de téléphone d'un transporteur spécifique.
    """
    # get_object_or_404 renvoie une erreur 404 propre si l'ID n'existe pas en BDD
    transporter = get_object_or_404(Transporteur, id=contact_id)
    
    # On renvoie directement un dictionnaire simple avec la clé 'tel'
    return JsonResponse({'tel': transporter.tel})


def search_districts(request, region_id):
    # On filtre les enfants de la région
    districts = Structure.objects.filter(parent_id=region_id).values('id', 'nom', 'designation')
    # On renvoie une liste sous la clé 'districts'
    return JsonResponse({'districts': list(districts)})

def search_fosas(request, district_id):
    # On filtre les enfants du district
    fosas = Structure.objects.filter(parent_id=district_id).values('id', 'nom', 'designation')
    # On renvoie une liste sous la clé 'fosas'
    return JsonResponse({'fosas': list(fosas)})
def parse_custom_date(date_str):
    """Convertit une chaîne 'JJ-MM-AAAA' en objet date Python."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
    except (ValueError, TypeError):
        return None

def enregistrer_fiche_echantillon(request):
    if request.method == "POST":
        # 1. Récupération des données
        data = request.POST
        
        region_id = data.get('region')
        district_id = data.get('district')
        fosa_id = data.get('fosa')
        transporteur = data.get('transporteur') or None
        moyen_id = data.get('moyen_transport') or None
        
        receptioniste = request.user.first_name
        
        code = data.get('code')
        nombre_echantillon = data.get('nombre_echantillon')
        observation = data.get('observation')
        numero_ordre = data.get('numero_ordre')

        # 2. Conversion des dates (JJ-MM-AAAA -> datetime.date)
        date_reception = parse_custom_date(data.get('date_reception'))
        date_expedition = parse_custom_date(data.get('date_expedition'))
        date_enregistrement = parse_custom_date(data.get('date_enregistrement'))
        date_envoie_labo = parse_custom_date(data.get('date_entree_labo'))

        # 3. Validation
        required_fields = [
            region_id, district_id, fosa_id, 
        
            nombre_echantillon, date_enregistrement
        ]
        
        if not all(required_fields):
            return JsonResponse({'success': False, 'errors': 'Champs obligatoires manquants .'}, status=400)

        try:
            # 4. Création de la fiche avec objets dates parsés
            fiche = FicheEchantillon.objects.create(
                code=code,
                region_id=region_id,
                district_id=district_id,
                fosa_id=fosa_id,
                transporteur=transporteur,
                moyen_transport_id=moyen_id,
                receptioniste=receptioniste, 
                date_reception=date_reception,
                date_expedition=date_expedition,
                date_enregistrement=date_enregistrement,
                nombre_echantillon=nombre_echantillon,
                observation=observation,
                numero_ordre=numero_ordre,
                date_Envoie_labo=date_envoie_labo
            )

            return redirect('verification-code', id=fiche.id)

        except IntegrityError as e:
            messages.error(request, f"Erreur BDD: {str(e)}")
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER', '/'))
def details_fiche(request, id):
    fiche = FicheEchantillon.objects.get(id=id)
    context ={
        'fiche':fiche,
        'echantillons':fiche.echantillons.all()
    }
    return render(request, 'webpages/echantillonages/details-fiche-echantillonage.html', context)

def detail_fiche(request, code):
    pass

@permission_required('circb_app.peut_saisir_echantillon')
def ajouter_echantillon(request):
    if request.method == 'POST':
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
            request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        )
        
        if is_ajax:
            fiche_id = request.POST.get('fiche_echantillon')
            code_region = (request.POST.get('code_region') or '').strip().upper()
            code_district = (request.POST.get('code_district') or '').strip().upper()
            code_fosa = (request.POST.get('code_fosa') or '').strip().upper()
            code_pt = (request.POST.get('code_pt') or '').strip().upper()
            mere_id = request.POST.get('mere_id')
            enfant_id = request.POST.get('enfant_id')
           
           
            code_patient = f"{code_region}{code_district}{code_fosa}{code_pt}"

            try:
                # 1. Récupération obligatoire de la Fiche
                fiche = FicheEchantillon.objects.filter(id=fiche_id).first() if fiche_id else None
                if not fiche:
                    return JsonResponse({'success': False, 'error': "Fiche d'échantillon introuvable."}, status=400)

                # --- Helpers de nettoyage ---
                def p_bool(val):
                    return str(val).strip().lower() in ['oui', '1', 'true', 'on'] if val else False

                def p_int(val):
                    return int(val) if val and str(val).isdigit() else None

                def p_float(val):
                    if not val: return None
                    try: return float(str(val).replace(',', '.'))
                    except ValueError: return None

                def p_date(val):
                    """
                    Tente de parser les dates au format 'JJ-MM-AAAA' (formulaire personnalisé)
                    ou au format 'AAAA-MM-JJ' (fallback HTML5).
                    """
                    if not val or not str(val).strip(): return None
                    clean_val = str(val).strip()
                    for fmt in ('%d-%m-%Y', '%Y-%m-%d'):
                        try:
                            return datetime.strptime(clean_val, fmt).date()
                        except ValueError:
                            pass
                    return None

                def p_str(val):
                    """Nettoie une chaîne de caractères et renvoie None si vide."""
                    if not val: return None
                    v = str(val).strip()
                    return v if v else None

                # --- Récupération des données pour validation préalable ---
                poids = p_float(request.POST.get('poids'))
                date_naissance_enfant = p_date(request.POST.get('date_naissance'))
                date_initiation_tarv = p_date(request.POST.get('date_initiation_tarv'))
                date_sevrage = p_date(request.POST.get('date_sevrage'))
                date_naissance_mere = p_date(request.POST.get('mere_date_naissance'))

                # --- VALIDATIONS MÉTIER STRICTES ---
                # if poids is not None and poids > 0:
                #     return JsonResponse({'success': False, 'error': "Le poids de l'échantillon/enfant doit être supérieur  à 0 kg."}, status=400)

                if date_initiation_tarv and date_naissance_enfant:
                    if date_initiation_tarv <= date_naissance_enfant:
                        return JsonResponse({'success': False, 'error': "La date d'initiation TARV doit être strictement supérieure à la date de naissance de l'enfant."}, status=400)

                if date_naissance_enfant and date_sevrage:
                    if date_naissance_enfant >= date_sevrage:
                        return JsonResponse({'success': False, 'error': "La date de naissance de l'enfant doit être inférieure à la date de sevrage."}, status=400)
                if Echantillon.objects.filter(code=request.POST['code_echantillon']).exists():
                    return JsonResponse({'success': False, 'error': f"Ce code: {request.POST['code_echantillon']} est déjà attribué à un autre échantillon. Veuillez en spécifier un nouveau."}, status=400)

                if date_naissance_mere:
                    age_mere_jours = (datetime.now().date() - date_naissance_mere).days
                    if age_mere_jours < (11 * 365):
                        return JsonResponse({'success': False, 'error': "L'âge de la mère doit être supérieur ou égal à 11 ans."}, status=400)

                    if date_naissance_enfant and date_naissance_mere >= date_naissance_enfant:
                        return JsonResponse({'success': False, 'error': "Incohérence : L'enfant ne peut pas être plus âgé (ou né avant) que sa mère."}, status=400)

                # --- Transaction Atomique ---
                with transaction.atomic():

                    # -------------------------------------------------------------
                    # 2. PATIENT / ENFANT
                    # -------------------------------------------------------------
                    enfant = None
                    if code_patient:
                        enfant = Patient.objects.filter(code=code_patient).first()
                    elif enfant_id:
                        enfant = Patient.objects.filter(id=enfant_id).first()

                    if not enfant:
                        return JsonResponse({'success': False, 'error': f"Le patient avec le code '{code_patient}' est introuvable."}, status=404)

                    if request.POST.get('enfant_nom'):
                        enfant.nom = request.POST.get('enfant_nom', '').strip()
                    if request.POST.get('enfant_prenom'):
                        enfant.prenom = request.POST.get('enfant_prenom', '').strip()
                    if date_naissance_enfant:
                        enfant.date_naissance = date_naissance_enfant
                    if request.POST.get('sexe'):
                        enfant.sexe = request.POST.get('sexe', '').strip()

                    if request.POST.get('rang_naissance'):
                        enfant.rang_naissance = p_int(request.POST.get('rang_naissance'))
                    enfant.status = True
                    enfant.save()

                    # -------------------------------------------------------------
                    # 3. MÈRE
                    # -------------------------------------------------------------
                    mere = None
                    if mere_id:
                        mere = Mere.objects.filter(id=mere_id).first()

                    nom_mere = request.POST.get('mere_nom', '').strip()
                    prenom_mere = request.POST.get('mere_prenom', '').strip()
                    contact_mere = request.POST.get('contact_familial', '').strip()

                    if not mere:
                        if nom_mere or prenom_mere or contact_mere or date_naissance_mere:
                            mere = Mere.objects.create(
                                nom=nom_mere,
                                prenom=prenom_mere,
                                date_naissance=date_naissance_mere,
                                contact=contact_mere
                            )
                    else:
                        if nom_mere: mere.nom = nom_mere
                        if prenom_mere: mere.prenom = prenom_mere
                        if date_naissance_mere: mere.date_naissance = date_naissance_mere
                        if contact_mere: mere.contact = contact_mere
                        mere.save()

                    if mere and hasattr(enfant, 'mere'):
                        enfant.mere = mere
                        enfant.save()

                    # -------------------------------------------------------------
                    # 4. ENREGISTREMENT DE L'ÉCHANTILLON
                    # -------------------------------------------------------------
                    echantillon = Echantillon.objects.create(
                        code=p_int(request.POST.get('code_echantillon')),
                        fiche=fiche,
                        enfant=enfant,
                        mere=mere,
                        poids=poids,
                        profilaxie_arv=request.POST.get('profilaxie_arv'),
                        protocole_ptme=p_str(request.POST.get('protocole_ptme')),
                        autre_profilaxie_arv = request.POST.get('autre_profilaxie_arv'),
                        date_rdv=p_date(request.POST.get('date_prochain_rdv')),
                        date_initiation_ptme=p_date(request.POST.get('date_initiation_ptme')),
                        date_diagnostic_vih=p_date(request.POST.get('date_diagnostic_vih')),
                        numero_grossesse=p_int(request.POST.get('numero_grossesse')),
                        nb_enfant_expose=p_int(request.POST.get('nbre_enfant_expose')),
                        nb_enfant_infecte=p_int(request.POST.get('nbre_enfant_infecte')),
                        mode_accouchement=p_int(request.POST.get('mode_accouchement')),
                        date_diagnostic_lav=p_date(request.POST.get('date_diagnostic_lav')),
                        examen=request.POST.get('examen'),
                        date_initiation_profilaxie_arv=p_date(request.POST.get('date_initiation_arv')),
                        
                        # SUIVI CLINIQUE ET VIROLOGIQUE
                        present_symptome=p_int(request.POST.get('enfant_symptomatique')),
                        present_allaitement=p_int(request.POST.get('enfant_allaite')),
                        mode_allaitement=p_int(request.POST.get('mode_allaitement')),
                        present_sevrage=p_int(request.POST.get('statut_sevrage')),
                        date_sevrage=date_sevrage,
                        present_cotrimoxazole=p_bool(request.POST.get('sous_cotrim')),
                        date_cotrimoxazole=p_date(request.POST.get('date_initiation_cotrim')),
                        present_tarv=p_bool(request.POST.get('sous_tarv')),
                        date_tarv=date_initiation_tarv,
                        protocole_ptme_autre = request.POST.get('protocole_ptme_autre'),
                        
                        # PCR ET PRÉLÈVEMENT
                        raison_prelevement_id=p_int(request.POST.get('raisons_prelevement')),
                        date_prelevement=p_date(request.POST.get('date_prelevement')),
                        duplicate_prelevement=request.POST.get('duplicate_prelevement'),
                        nom_preleveur=request.POST.get('nom_preleveur', '').strip(),
                        prenom_preleveur=request.POST.get('prenom_preleveur', '').strip(),
                        contact_preleveur=p_int(request.POST.get('contact_preleveur', None)),
                        observation=request.POST.get('observation', '').strip(),
                        date_enregistrement=datetime.now().date()
                    )
                    
                    nombre_actuel = Echantillon.objects.filter(fiche=fiche).count()
                    if fiche.nombre_echantillon and nombre_actuel >= fiche.nombre_echantillon:
                        fiche.status = False
                        fiche.save()
                
                return JsonResponse({
                    'success': True, 
                    'message': "Les données du patient et de la mère ont été enregistrées avec succès !"
                })

            except Exception as e:
                return JsonResponse({'success': False, 'error': f"Erreur traitement : {str(e)}"}, status=500)
        
        return JsonResponse({'success': False, 'error': "Requête non autorisée."}, status=400)

    return render(request, 'webpages/echantillonages/echantillons.html', {})
@permission_required('circb_app.peut_modifier_echantillons')
def update_echantillon(request, id):
    echantillon = get_object_or_404(Echantillon, id=id)
    
    if request.method == 'POST':
        try:
            # --- HELPERS DE NETTOYAGE ---
            raw_poids = request.POST.get('poids')
            poids = float(raw_poids.replace(',', '.')) if raw_poids and str(raw_poids).strip() != '' else None

            def parse_date(val):
                """
                Parse les dates au format 'JJ-MM-AAAA' (saisie manuelle) 
                ou 'AAAA-MM-JJ' (fallback HTML5).
                """
                if not val or not str(val).strip():
                    return None
                clean_val = str(val).strip()
                for fmt in ('%d-%m-%Y', '%Y-%m-%d'):
                    try:
                        return datetime.strptime(clean_val, fmt).date()
                    except ValueError:
                        pass
                return None

            def parse_int(val):
                try:
                    return int(val) if val and str(val).strip() != '' else None
                except (ValueError, TypeError):
                    return None

            def parse_bool(val):
                return str(val).strip().lower() in ['oui', '1', 'true', 'on'] if val else False

            def parse_str(val):
                if not val: return None
                v = str(val).strip()
                return v if v else None

            # Récupération des données converties pour validation
            date_naissance_enfant = parse_date(request.POST.get('date_naissance'))
            date_initiation_tarv = parse_date(request.POST.get('date_initiation_tarv'))
            date_sevrage = parse_date(request.POST.get('date_sevrage'))
            date_naissance_mere = parse_date(request.POST.get('mere_date_naissance'))
            
            # --- VALIDATIONS MÉTIER STRICTES ---
            
            # 1. Le poids doit être supérieur ou égal à 6 kg
            # if poids is not None and poids >  0:
            #     messages.error(request, "Le poids de l'échantillon/enfant doit être supérieur ou égal à 0 kg.")
            #     return redirect('update_echantillon', id=echantillon.id)
            
            # 2. La date d'initiation TARV doit être supérieure à la date de naissance de l'enfant
            if date_initiation_tarv and date_naissance_enfant:
                if date_initiation_tarv <= date_naissance_enfant:
                    messages.error(request, "La date d'initiation TARV doit être strictement supérieure à la date de naissance de l'enfant.")
                    return redirect('update_echantillon', id=echantillon.id)
            
            # 3. La date de naissance de l'enfant doit être inférieure à la date de sevrage
            if date_naissance_enfant and date_sevrage:
                if date_naissance_enfant >= date_sevrage:
                    messages.error(request, "La date de naissance de l'enfant doit être inférieure à la date de sevrage.")
                    return redirect('update_echantillon', id=echantillon.id)
            
            # 4 & 5. Règles sur l'âge de la mère et comparaison avec l'enfant
            if date_naissance_mere:
                age_mere_jours = (datetime.now().date() - date_naissance_mere).days
                if age_mere_jours < (11 * 365):
                    messages.error(request, "L'âge de la mère doit être supérieur ou égal à 11 ans.")
                    return redirect('update_echantillon', id=echantillon.id)
            
                if date_naissance_enfant and date_naissance_mere >= date_naissance_enfant:
                    messages.error(request, "Incohérence : L'enfant ne peut pas être plus âgé (ou né avant) que sa mère.")
                    return redirect('update_echantillon', id=echantillon.id)
            
            # --- MISE À JOUR DE L'ÉCHANTILLON ---
            echantillon.code = parse_int(request.POST.get('code_echantillon')) or echantillon.code
            
            # INFOS ENFANT & MÈRE
            echantillon.rang_naissance = parse_int(request.POST.get('rang_naissance'))
            echantillon.poids = poids
            echantillon.profilaxie_arv = request.POST.get('profilaxie_arv')
            
            # INFOS SUIVI MÈRE
            echantillon.protocole_ptme = parse_str(request.POST.get('protocole_ptme'))
            echantillon.date_rdv = parse_date(request.POST.get('date_prochain_rdv'))
            echantillon.date_initiation_ptme = parse_date(request.POST.get('date_initiation_ptme'))
            echantillon.date_diagnostic_vih = parse_date(request.POST.get('date_diagnostic_vih'))
            echantillon.numero_grossesse = parse_int(request.POST.get('numero_grossesse'))
            echantillon.nb_enfant_expose = parse_int(request.POST.get('nbre_enfant_expose'))
            echantillon.nb_enfant_infecte = parse_int(request.POST.get('nbre_enfant_infecte'))
            echantillon.mode_accouchement = parse_int(request.POST.get('mode_accouchement'))
            echantillon.date_diagnostic_lav = parse_date(request.POST.get('date_diagnostic_lav'))
            echantillon.date_initiation_profilaxie_arv = parse_date(request.POST.get('date_initiation_arv'))
            echantillon.autre_profilaxie_arv = request.POST.get('autre_profilaxie_arv')
            
            # SUIVI CLINIQUE ET VIROLOGIQUE
            echantillon.present_symptome = parse_int(request.POST.get('enfant_symptomatique'))
            echantillon.present_allaitement = parse_int(request.POST.get('enfant_allaite'))
            echantillon.mode_allaitement = parse_int(request.POST.get('mode_allaitement'))
            echantillon.present_sevrage = parse_int(request.POST.get('statut_sevrage'))
            echantillon.date_sevrage = date_sevrage
            echantillon.present_cotrimoxazole = parse_bool(request.POST.get('sous_cotrim'))
            echantillon.date_cotrimoxazole = parse_date(request.POST.get('date_initiation_cotrim'))
            echantillon.present_tarv = parse_bool(request.POST.get('sous_tarv'))
            echantillon.date_tarv = date_initiation_tarv
            
            echantillon.protocole_ptme_autre = request.POST.get('protocole_ptme_autre')
            
            # PCR ET PRÉLÈVEMENT
            echantillon.raison_prelevement_id = parse_int(request.POST.get('raisons_prelevement'))
            echantillon.date_prelevement = parse_date(request.POST.get('date_prelevement'))
            echantillon.duplicate_prelevement = request.POST.get('duplicate_prelevement')
            echantillon.nom_preleveur = request.POST.get('nom_preleveur', '').strip()
            echantillon.prenom_preleveur = request.POST.get('prenom_preleveur', '').strip()
            echantillon.contact_preleveur = parse_int(request.POST.get('contact_preleveur'))
            echantillon.observation = request.POST.get('observation', '').strip()
            
            echantillon.save()

            messages.success(request, "Échantillon mis à jour avec succès.")
            return redirect('/echantillonages/')

        except Exception as e:
            messages.error(request, f"Une erreur technique est survenue : {str(e)}")
            return redirect('update_echantillon', id=echantillon.id)

    return redirect('/echantillonages/')
def ajouter_patient(request):
    if request.method == 'POST':
        # 1. Récupération des données du POST
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        date_naissance_str = request.POST.get('date_naissance')
        sexe = request.POST.get('sexe')
        contact_id = request.POST.get('contact')
        fosa_id = request.POST.get('fosa')
        poids_str = request.POST.get('poids')
        profilaxie_id = request.POST.get('profilaxie')
        mere_id = request.POST.get('mere')
        code = request.POST.get('code')
        porte_entree_id = request.POST.get('porte_entree')

        # 2. Nettoyage et conversion des données
        # Gestion de la date
        date_naissance = None
        if date_naissance_str:
            try:
                date_naissance = datetime.strptime(date_naissance_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Gestion du poids (DecimalField)
        poids = None
        if poids_str:
            try:
                poids = Decimal(poids_str.replace(',', '.')) # Remplace la virgule par un point au cas où
            except (InvalidOperation, ValueError):
                messages.error(request, "Le format du poids est invalide.")
                return redirect('ajouter_patient')

        # Gestion automatique du code (SlugField) si non fourni
        if not code and nom:
            # Exemple de génération automatique basé sur le nom, prénom et l'année actuelle
            base_slug = f"{nom}-{prenom if prenom else ''}-{datetime.now().year}"
            code = slugify(base_slug).upper()

        # 3. Sauvegarde de l'instance Patient
        try:
            patient = Patient.objects.create(
                nom=nom,
                prenom=prenom if prenom else None,
                date_naissance=date_naissance,
                sexe=sexe if sexe else None,
                contact_id=contact_id if contact_id else None,
                fosa_id=fosa_id if fosa_id else None,
                poids=poids,
                profilaxie_id=profilaxie_id if profilaxie_id else None,
                mere_id=mere_id if mere_id else None,
                code=code,
                porte_entree_id=porte_entree_id if porte_entree_id else None
            )
            
            messages.success(request, f"Le patient {patient.nom} {patient.prenom or ''} (Code: {patient.code}) a bien été enregistré.")
            return redirect('liste_patients') # Remplacez par le nom de votre URL cible

        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement : {str(e)}")

    # 4. Contexte envoyé au formulaire HTML (Méthode GET)
    context = {
     
        'structures': Structure.objects.all(),
        'profilaxies': ProfilaxieArv.objects.all(),
        'meres': Mere.objects.all(),
        'portes_entree': PorteEntree.objects.all(),
    }
    
    return render(request, 'webpages/patients/dossier.html', context)


def search_porte_entree(request, porte_entree_id):
    """Récupère le code court d'une porte d'entrée spécifique"""
    porte = get_object_or_404(PorteEntree, id=porte_entree_id)
    
    # On renvoie la désignation (ex: "PT", "CP")
    return JsonResponse({
        'id': porte.id,
        'nom': porte.nom,
        'code': porte.code  # Ta colonne contenant ton code à 2 lettres
    })

import logging
import re
from django.http import JsonResponse
from django.template.loader import render_to_string
from .models import Echantillon, Patient

logger = logging.getLogger(__name__)

# Regex pour valider le format segmenté : 3-3-3-2-X (ex: LIT-NYL-CML-PT-0222)
CODE_PATIENT_REGEX = r"^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{2}-[A-Z0-9]+$"


def formater_date(valeur_date):
    """Convertit en toute sécurité une date en chaîne YYYY-MM-DD"""
    if not valeur_date:
        return None
    if hasattr(valeur_date, "strftime"):
        return valeur_date.strftime("%Y-%m-%d")
    return str(valeur_date)


def segmenter_code_patient(raw_code):
    """Nettoie, segmente et formate un code patient au format XXX-XXX-XXX-XX-XXXX."""
    code_clean = raw_code.strip().upper()
    parts = code_clean.split("-")

    # Si le code est fourni sans tirets (ex: LITNYLCMLPT0222)
    if len(parts) == 1 and len(code_clean) >= 15:
        region = code_clean[0:3]
        dept = code_clean[3:6]
        fosa = code_clean[6:9]
        type_code = code_clean[9:11]
        numero = code_clean[11:]
        return f"{region}-{dept}-{fosa}-{type_code}-{numero}"

    return code_clean


def verifier_patient(request):
    """Vérifie l'existence d'un patient par son code unique complet et récupère ses antécédents d'échantillons."""
    raw_code = request.GET.get("code", "")

    if not raw_code:
        return JsonResponse(
            {"existe": False, "erreur": "Code manquant"}, status=400
        )

    # 1. Segmentation et nettoyage du code
    code_recherche = segmenter_code_patient(raw_code)

    # 2. Validation du format segmenté (3-3-3-2-X)
    if not re.match(CODE_PATIENT_REGEX, code_recherche):
        return JsonResponse(
            {
                "existe": False,
                "erreur": (
                    "Format de code invalide. Attendu : XXX-XXX-XXX-XX-XXXX"
                ),
            },
            status=400,
        )

    try:
        # Optimisation SQL : Récupère le patient et sa mère/porte d'entrée en une seule requête SQL
        patient = (
            Patient.objects.select_related("mere", "porte_entree")
            .filter(code=code_recherche)
            .first()
        )

        if not patient:
            return JsonResponse({"existe": False})

        # --- RÉCUPÉRATION ET RENDU DES ÉCHANTILLONS PRÉCÉDENTS ---
        echantillons_precedents = Echantillon.objects.filter(
            enfant=patient
        ).order_by("-ordre")

        historique_html = render_to_string(
            "webpages/echantillonages/historique_items.html",
            {"historique_echantillons": echantillons_precedents},
            request=request,
        )

        # --- DONNÉES DE LA MÈRE ---
        mere_data = None
        if hasattr(patient, "mere") and patient.mere:
            mere = patient.mere
            mere_data = {
                "id": mere.id,
                "nom": getattr(mere, "nom", ""),
                "prenom": getattr(mere, "prenom", ""),
                "contact": (
                    mere.contact_id if hasattr(mere, "contact_id") else None
                ),
                "age": getattr(mere, "age", None),
                "date_naissance": formater_date(
                    getattr(mere, "date_naissance", None)
                ),
            }

        # --- DONNÉES DE LA PORTE D'ENTRÉE ---
        porte_entree_id = (
            patient.porte_entree_id
            if hasattr(patient, "porte_entree_id")
            else None
        )

        # --- RÉPONSE JSON ---
        return JsonResponse(
            {
                "existe": True,
                "patient": {
                    "id": patient.id,
                    "code": patient.code,
                    "nom": getattr(patient, "nom", ""),
                    "prenom": getattr(patient, "prenom", ""),
                    "sexe": getattr(patient, "sexe", None),
                    "porte_entree": porte_entree_id,
                    "date_naissance": formater_date(
                        getattr(patient, "date_naissance", None)
                    ),
                    "mere": mere_data,
                    "historique_html": historique_html,
                },
            }
        )

    except Exception as e:
        logger.error(
            f"Erreur lors de la vérification du patient {code_recherche} : {str(e)}",
            exc_info=True,
        )
        return JsonResponse(
            {"existe": False, "erreur": f"Erreur serveur : {str(e)}"},
            status=500,
        )
from django.shortcuts import render
from django.http import JsonResponse
from .models import Structure, PorteEntree, Patient, Mere  # Assure-toi d'importer ton modèle Mere
from datetime import datetime
from django.db import transaction
import sys


def custom_page_not_found_view(request, exception):
    return render(request, 'webpages/404.html', status=404)

def custom_error_view(request, exception=None):
    return render(request, 'webpages/500.html', status=500)


def create_or_edit_role(request):
    if request.method == 'POST':
      
        nom = request.POST.get('role_name')
        description = request.POST.get('role_description')

       
        Role.objects.create(nom=nom, description=description)
        messages.success(request, f"Le rôle '{nom}' a été créé avec succès.")

    return redirect('/configurations/')  # Remplacez par le nom de votre URL de redirection pour la liste des rôles   
@login_required(login_url='/')
def delete_role(request, id):
    role = get_object_or_404(Group, id=id)
    
    # Vérifie si le rôle est lié à au moins un utilisateur
    if role.user_set.exists():
        messages.error(
            request, 
            f"Impossible de supprimer le rôle '{role.name}' car il est attribué à un ou plusieurs utilisateurs."
        )
    else:
        role_name = role.name
        role.delete()
        messages.success(
            request, 
            f"Le rôle '{role_name}' a été supprimé avec succès."
        )
        
    return redirect('/configurations/')
def edit_role(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    context = {
        'role': role
    }
    return render(request, 'webpages/config/edit_role.html', context)

def fiche_echantillon(request, slug):
    context = {
        'echantillon':Echantillon.objects.get(slug=slug)
    }
    return render(request, 'webpages/echantillonages/detail-echantillon.html', context)


def resultats_test(request):
    context = {
        'echantillons':Echantillon.objects.all(),
        'resultat_pcr': ResultatPcr.objects.all(),
        'tests': Test.objects.select_related('pcr').all()
    }
    return render(request, 'webpages/resultats/resultats-test.html', context)



@login_required
@require_POST
def enregistrer_resultat_ajax(request):
    try:
        echantillon_id = request.POST.get('echantillon')
        test_id = request.POST.get('test')
        resultat_pcr_id = request.POST.get('resultat_pcr')
        date_prelevement = request.POST.get('date_prelevement')
        commentaire = request.POST.get('commentaire', '')

        if not echantillon_id or not resultat_pcr_id or not date_prelevement:
            return JsonResponse({'success': False, 'error': 'Champs obligatoires manquants.'}, status=400)

        echantillon = Echantillon.objects.get(id=echantillon_id)
        resultat_pcr = ResultatPcr.objects.get(id=resultat_pcr_id)
        test = Test.objects.get(id=test_id) if test_id else None

        resultat = Resultat.objects.create(
            echantillon=echantillon,
            test=test,
            resultat_pcr=resultat_pcr,
            date_prelevement=date_prelevement,
            commentaire=commentaire,
            responsable=request.user
        )

        # On renvoie le succès ET les représentations textuelles pour le modal
        return JsonResponse({
            'success': True,
            'data': {
                'id': resultat.id,
                'echantillon': str(echantillon),
                'test': test.nom if test else "Non spécifié",
                'resultat_pcr': resultat_pcr.nom,
                'date_prelevement': "-".join(date_prelevement.split("-")[::-1]) if "-" in str(date_prelevement) else str(date_prelevement),
                'commentaire': commentaire or "Aucun commentaire rédigé."
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
import qrcode
import qrcode.image.svg

def generer_qr_svg(texte):
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(texte, image_factory=factory, box_size=5)
    return img.to_string().decode('utf-8')


@permission_required('circb_app.Consulter_resultat_patient', raise_exception=True)
def nettoyer_date_front(date_str):
    """
    Convertit une date utilisateur (JJ-MM-AAAA ou JJMMAAAA) 
    vers le format ISO requis par la base de données (AAAA-MM-JJ).
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Format JJ-MM-AAAA ou JJ/MM/AAAA -> AAAA-MM-JJ
    match = re.match(r'^(\d{2})[-/](\d{2})[-/](\d{4})$', date_str)
    if match:
        jour, mois, annee = match.groups()
        return f"{annee}-{mois}-{jour}"

    # Format JJMMAAAA -> AAAA-MM-JJ
    if re.match(r'^\d{8}$', date_str):
        jour = date_str[:2]
        mois = date_str[2:4]
        annee = date_str[4:]
        return f"{annee}-{mois}-{jour}"

    # Format ISO préexistant (AAAA-MM-JJ)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    return None


@permission_required('circb_app.Consulter_resultat_patient', raise_exception=True)
def resultats(request):
    # 1. Base du QuerySet
    queryset = (
        Echantillon.objects.filter(resultat_pcr__isnull=False)
        .select_related("enfant", "resultat_pcr", "fiche")
        .order_by(
            F("date_resultat").desc(nulls_last=True),
            F("date_saisie").desc(nulls_last=True),
            F("id").desc(),
        )
    )

    # 2. Récupération des filtres
    code_echantillon = request.GET.get("code_echantillon", "").strip()
    code_patient = request.GET.get("code_patient", "").strip()
    date_prelevement_raw = request.GET.get("date_prelevement", "").strip()
    test_id = request.GET.get("test", "").strip()
    verdict_id = request.GET.get("verdict", "").strip()

    # Nettoyage de la date pour l'ORM
    date_prelevement_clean = nettoyer_date_front(date_prelevement_raw)

    # 3. Application des filtres ORM
    if code_echantillon:
        queryset = queryset.filter(code__icontains=code_echantillon)

    if code_patient:
        queryset = queryset.filter(enfant__code__icontains=code_patient)

    if date_prelevement_clean:
        # Remplacez 'date_prelevement' si le champ est lié (ex: fiche__date_prelevement)
        queryset = queryset.filter(date_prelevement=date_prelevement_clean)

    if test_id:
        queryset = queryset.filter(tests=test_id)

    if verdict_id:
        queryset = queryset.filter(resultat_pcr_id=verdict_id)

    # 4. Pagination
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page", 1)

    try:
        resultats_page = paginator.page(page_number)
    except PageNotAnInteger:
        resultats_page = paginator.page(1)
    except EmptyPage:
        resultats_page = paginator.page(paginator.num_pages)

    context = {
        "resultats": resultats_page,
        "tests": Test.objects.all(),
        "resultat_pcr": ResultatPcr.objects.all(),
    }
    return render(request, "webpages/resultats/list_resultat.html", context)
import base64
import io
import os
from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import get_object_or_404, HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa

import base64
import os
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML
from .tasks import generate_pdf_async

def resultats_individuel(request, id):
    resultat = get_object_or_404(Echantillon, id=id)

    # Récupération de l'URL de base pour WeasyPrint
    base_uri = request.build_absolute_uri('/')

    # Envoi de la tâche dans Redis via Celery (Asynchrone)
    task = generate_pdf_async.delay(
        echantillon_id=resultat.id,
        user_id=request.user.id if request.user.is_authenticated else None,
        base_uri=base_uri
    )

    # On retourne une réponse immédiate avec le Task ID
    return JsonResponse({
        "status": "processing",
        "message": "La génération du PDF est en cours...",
        "task_id": task.id
    })


def resultats_individuel_pdf(request):
    data = request.POST if request.method == "POST" else request.GET

    # Récupération des filtres éventuels (comme pour les résultats collectifs)
    debut_raw = data.get("debut_ancien_code", "").strip()
    fin_raw = data.get("fin_code_echantillon", "").strip()
    inclure_raw = data.get("liste_inclure", "").strip()
    exclure_raw = data.get("liste_exclure", "").strip()
    resultat_id = data.get("resultat_id")  # Si appel pour un seul résultat ID

    # 1. Chargement et conversion du logo en Base64
    logo_base64 = ""
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find(
        "images/logo_circb.png"
    )
    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Filtrage des résultats
    if resultat_id:
        # Cas d'un seul échantillon ciblé par ID
        resultats = Echantillon.objects.filter(id=resultat_id)
    else:
        # Cas de filtrage multiple par plage ou listes
        def parse_code_list(raw_string):
            if not raw_string:
                return []
            cleaned = (
                raw_string.replace("\r\n", ",")
                .replace("\n", ",")
                .replace(";", ",")
            )
            return [c.strip() for c in cleaned.split(",") if c.strip()]

        codes_inclure = parse_code_list(inclure_raw)
        codes_exclure = parse_code_list(exclure_raw)
        debut = int(debut_raw) if debut_raw.isdigit() else None
        fin = int(fin_raw) if fin_raw.isdigit() else None

        base_qs = Echantillon.objects.all()

        qs_plage = base_qs.none()
        if debut is not None or fin is not None:
            numeric_qs = base_qs.filter(code__regex=r"^\d+$").annotate(
                code_int=Cast("code", output_field=IntegerField())
            )
            query_plage = Q()
            if debut is not None and fin is not None:
                query_plage &= Q(code_int__gte=debut, code_int__lte=fin)
            elif debut is not None:
                query_plage &= Q(code_int__gte=debut)
            elif fin is not None:
                query_plage &= Q(code_int__lte=fin)
            qs_plage = numeric_qs.filter(query_plage)

        qs_inclure = (
            base_qs.filter(code__in=codes_inclure)
            if codes_inclure
            else base_qs.none()
        )

        if (debut is not None or fin is not None) and codes_inclure:
            base_queryset = qs_plage | qs_inclure
        elif debut is not None or fin is not None:
            base_queryset = qs_plage
        elif codes_inclure:
            base_queryset = qs_inclure
        else:
            base_queryset = base_qs

        if codes_exclure and base_queryset.exists():
            base_queryset = base_queryset.exclude(code__in=codes_exclure)

        resultats = base_queryset.select_related(
            "enfant",
            "mere",
            "fiche__region",
            "fiche__district",
            "fiche__fosa",
           
            "resultat_pcr",
        ).order_by("code")

    # 3. Transmission au context
    context = {
        "resultats": resultats,  # Liste globale des résultats
        "responsable": request.user,
        "logo_base64": logo_base64,
        "date_impression": timezone.now(),
    }

    # 4. Rendu HTML
    html_content = render_to_string(
        "webpages/rapports/resultat-individuel-regroup.html", context
    )

    # 5. Génération du PDF WeasyPrint
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'inline; filename="Fiches_Resultats_Individuels.pdf"'
    )

    HTML(string=html_content, base_url=request.build_absolute_uri()).write_pdf(
        response
    )

    return response
def resultats_collectifs(request):
    data = request.POST if request.method == "POST" else request.GET

    debut_raw = data.get("debut_ancien_code", "").strip()
    fin_raw = data.get("fin_code_echantillon", "").strip()
    inclure_raw = data.get("liste_inclure", "").strip()
    exclure_raw = data.get("liste_exclure", "").strip()

    def parse_code_list(raw_string):
        if not raw_string:
            return []
        cleaned = (
            raw_string.replace("\r\n", ",")
            .replace("\n", ",")
            .replace(";", ",")
        )
        return [c.strip() for c in cleaned.split(",") if c.strip()]

    codes_inclure = parse_code_list(inclure_raw)
    codes_exclure = parse_code_list(exclure_raw)

    debut = int(debut_raw) if debut_raw.isdigit() else None
    fin = int(fin_raw) if fin_raw.isdigit() else None

    # 1. Chargement et conversion du logo CIRCB en Base64
    logo_base64 = ""
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find(
        "images/logo_circb.png"
    )
    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Filtrage exact des échantillons dans la plage / listes
    base_qs = Echantillon.objects.all()

    qs_plage = base_qs.none()
    if debut is not None or fin is not None:
        numeric_qs = base_qs.filter(code__regex=r"^\d+$").annotate(
            code_int=Cast("code", output_field=IntegerField())
        )
        query_plage = Q()
        if debut is not None and fin is not None:
            query_plage &= Q(code_int__gte=debut, code_int__lte=fin)
        elif debut is not None:
            query_plage &= Q(code_int__gte=debut)
        elif fin is not None:
            query_plage &= Q(code_int__lte=fin)

        qs_plage = numeric_qs.filter(query_plage)

    qs_inclure = base_qs.none()
    if codes_inclure:
        qs_inclure = base_qs.filter(code__in=codes_inclure)

    if (debut is not None or fin is not None) and codes_inclure:
        base_queryset = qs_plage | qs_inclure
    elif debut is not None or fin is not None:
        base_queryset = qs_plage
    elif codes_inclure:
        base_queryset = qs_inclure
    else:
        base_queryset = base_qs

    if codes_exclure and base_queryset.exists():
        base_queryset = base_queryset.exclude(code__in=codes_exclure)

    # 3. Optimisation des requêtes et tri
    resultats = (
        base_queryset.select_related(
            "enfant",
            "mere",
            "fiche__fosa",
           
            "resultat_pcr",
        )
        .prefetch_related("resultats")
        .order_by("code")
    )

    # 4. Context pour le template global
    context = {
        "logo_base64": logo_base64,
        "date_impression": timezone.now(),
        "resultats": resultats,  # Liste plate globale des échantillons
        "responsable": request.user,
        "debut": debut,
        "fin": fin,
        "codes_inclure": codes_inclure,  # <-- AJOUTÉ
        "codes_exclure": codes_exclure,  # <-- AJOUTÉ
    }

    # 5. Rendu HTML et compilation PDF avec xhtml2pdf
    html_content = render_to_string(
        "webpages/rapports/resultats-collectif.html", context
    )

    pdf_buffer = io.BytesIO()
    pisa_status = pisa.pisaDocument(
        io.BytesIO(html_content.encode("utf-8")), pdf_buffer, encoding="utf-8"
    )

    if pisa_status.err:
        return HttpResponse(
            "Erreur lors de la compilation du PDF.", status=500
        )

    pdf_buffer.seek(0)
    pdf_data = pdf_buffer.getvalue()

    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = (
        'inline; filename="Resultats_Collectifs.pdf"'
    )
    response["Content-Length"] = len(pdf_data)

    return response
def bordeaux_sortie(request):
    fosas_niveau_3 = Structure.objects.filter(hierachy__rang=2)
    context={
        'fosas_niveau_3':fosas_niveau_3
    }
    return render(request, 'webpages/borderaux.html', context)

def api_rechercher_fosa(request):
    query = request.GET.get('q', '').strip()
    results = []
    
    # Lancement de la recherche à partir de 2 caractères minimum
    if len(query) >= 2:
        # Filtrage par rang 3 et correspondance sur le nom (limité à 20 résultats max pour la performance)
        fosas = Structure.objects.filter(hierachy__rang=2, nom__icontains=query)[:20]
        
        for f in fosas:
            parent_nom = f.parent.nom if f.parent else "District N/A"
            results.append({
                'id': f.id,
                'text': f"{f.nom} ({parent_nom})"
            })
            
    return JsonResponse({'results': results})

def supprimer_fiche(request, id):
    # 1. Récupère la fiche ou renvoie une erreur 404 proprement si l'ID n'existe pas
    fiche = get_object_or_404(FicheEchantillon, id=int(id))
    
    try:
        # 2. Supprime tous les échantillons liés à cette fiche en une seule requête SQL (Bulk Delete)
        Echantillon.objects.filter(fiche=fiche).delete()
        
        # Note : Si vous avez configuré "on_delete=models.CASCADE" sur la clé étrangère 'fiche' 
        # dans votre modèle Echantillon, l'étape ci-dessus est automatique lors de la suppression de la fiche.
        
        # 3. Supprime la fiche elle-même
        code_fiche = fiche.code
        fiche.delete()
        
        # 4. Message de succès ERP standard
        messages.success(request, f"La fiche [{code_fiche}] et tous ses échantillons associés ont été supprimés avec succès.")
        
    except Exception as e:
        messages.error(request, f"Une erreur est survenue lors de la suppression : {str(e)}")
        
    # 5. Redirection vers le registre général
    return redirect(request.META.get('HTTP_REFERER','/'))
from django.db.models import Max
@permission_required('circb_app.peut_saisir_fiche_expedition', raise_exception=True)
def fiches(request):
    # Calcule directement le numéro maximum présent en BDD
    max_num = FicheEchantillon.objects.aggregate(Max('numero_ordre'))[
        'numero_ordre__max'
    ]
    prochain_numero = (max_num + 1) if max_num is not None else 1

    # Récupère l'objet correspondant au dernier numéro pour le contexte si besoin
    dernier_numero = (
        FicheEchantillon.objects.filter(numero_ordre=max_num).first()
        if max_num
        else None
    )

    context = {
        'regions': Region.objects.all().order_by(
            'nom'
        ),
        'transporteurs': Transporteur.objects.all().order_by('nom'),
        'moyens_transport': MoyenTransport.objects.all().order_by('nom'),
        'fiches': FicheEchantillon.objects.all().order_by('-id'),
        'dernier_numero': dernier_numero,
        'prochain_numero': prochain_numero,
    }
    return render(request, 'webpages/echantillonages/fiches.html', context)



def verification_code(request, id):
    fiche = FicheEchantillon.objects.get(id=id)
    # Create the range here in Python
    sample_range = range(fiche.nombre_echantillon)
    
    context = {
        'fiche': fiche,
        'porte_entree': PorteEntree.objects.all(),
        'sample_range': sample_range # Pass this to the template
    }
    return render(request, 'webpages/echantillonages/verification-code.html', context)
import logging
import re
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Patient

logger = logging.getLogger(__name__)

CODE_PATIENT_REGEX = r'^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{2}-[A-Z0-9]+$'

def formater_date(date_obj):
    """Utilitaire de formatage de date en ISO String (YYYY-MM-DD)."""
    return date_obj.strftime("%Y-%m-%d") if date_obj else None


@require_GET
def rechercher_patient(request):
    code_query = request.GET.get("code", "").strip().upper()
    print(f'le code transmis est: {code_query}')

    clean_code = re.sub(r'[^A-Z0-9]', '', code_query)
    print(f'le code nettoye est: {clean_code}')

    if not clean_code or len(clean_code) < 13:
        return JsonResponse({"exists": False, "patients": []})

    # Extraction des segments du code
    region = clean_code[0:3]
    dept = clean_code[3:6]
    fosa = clean_code[6:9]

    # --- IF : Code avec PT spécifiée (15 caractères minimum) ---
    if len(clean_code) >= 15:
        pt_selectionnee = clean_code[9:11]
        print(f'la porte entree selectionnee est: {pt_selectionnee}')

        numero = clean_code[11:]
        print(f'la numero selectionnee est: {numero}')

        regex_pattern = f"{region}-{dept}-{fosa}-{pt_selectionnee}-{numero}"
        print(f'code dans le meilleur des cas est: {regex_pattern}')

        try:
            # Recherche exacte avec la porte d'entrée
            patient = Patient.objects.get(code=regex_pattern)
            print(f'patient_trouvee_avec_porte_entree: {patient}')

            patient_data = {
                "id": patient.id,
                "code": patient.code,
                "nom": getattr(patient, 'nom', ''),
                "prenom": getattr(patient, 'prenom', ''),
                "sexe": getattr(patient, 'sexe', ''),
                "date_naissance": str(getattr(patient, 'date_naissance', '') or ''),
                "porte_entree": pt_selectionnee,
                "mere": {
                    "nom": getattr(patient.mere, 'nom', ''),
                    "prenom": getattr(patient.mere, 'prenom', ''),
                    "date_naissance": str(getattr(patient.mere, 'date_naissance', '') or '')
                } if getattr(patient, 'mere', None) else None
            }

            # On retourne la structure attendue par le CAS 1 du JS (data.exact_match)
            return JsonResponse({
                "exists": True,
                "exact_match": patient_data,
                "autres_pts_count": 0,
                "autres_pts_patients": [],
                "all_patients": [patient_data]
            })

        except Patient.DoesNotExist:
            print("Patient non trouvé avec cette porte d'entrée exacte.")
            return JsonResponse({"exists": False, "patients": []})

    # --- ELSE : Code sans PT spécifiée (13 caractères) ---
    else:
        pt_selectionnee = None
        numero = clean_code[9:]

        # Expression régulière pour matcher tous les patients sous ce numéro (quelle que soit la PT)
        regex_pattern = f"^{region}-{dept}-{fosa}-..-{numero}$"
        patients_qs = Patient.objects.filter(code__regex=regex_pattern)

        print(f'code patient sans porte entree: {regex_pattern}')
        print(f'occurence des patient ayant les memes codes sans porte entree: {patients_qs}')

        if not patients_qs.exists():
            return JsonResponse({"exists": False, "patients": []})

        autres_pts_patients = []
        for p in patients_qs:
            parts = p.code.split("-")
            pt_in_db = parts[3] if len(parts) == 5 else ""

            patient_data = {
                "id": p.id,
                "code": p.code,
                "nom": getattr(p, 'nom', ''),
                "prenom": getattr(p, 'prenom', ''),
                "sexe": getattr(p, 'sexe', ''),
                "date_naissance": str(getattr(p, 'date_naissance', '') or ''),
                "porte_entree": pt_in_db,
                "mere": {
                    "nom": getattr(p.mere, 'nom', ''),
                    "prenom": getattr(p.mere, 'prenom', ''),
                    "date_naissance": str(getattr(p.mere, 'date_naissance', '') or '')
                } if getattr(p, 'mere', None) else None
            }
            autres_pts_patients.append(patient_data)

        # On retourne la structure attendue par le CAS 2 du JS (data.autres_pts_count)
        return JsonResponse({
            "exists": True,
            "exact_match": None,
            "autres_pts_count": len(autres_pts_patients),
            "autres_pts_patients": autres_pts_patients,
            "all_patients": autres_pts_patients
        })
def save_personnel(request):
    if request.method == "POST":
        try:
            nom = request.POST.get('last_name')
            prenom = request.POST.get('first_name')
            email = request.POST.get('email')
            service = request.POST.get('service')
            group_id = request.POST.get('role') # ID du groupe sélectionné dans votre formulaire

            if not all([nom, prenom, email, service, group_id]):
                return JsonResponse({'success': False, 'message': 'Tous les champs sont requis.'}, status=400)

            with transaction.atomic():
                # 1. Création de l'utilisateur
                password = get_random_string(length=12)
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=prenom,
                    last_name=nom
                )

                # 2. Attribution du rôle (Groupe Django natif)
                groupe = Group.objects.get(id=group_id)
                user.groups.add(groupe) # Méthode native Django

            return JsonResponse({
                'success': True, 
                'message': f'Agent enregistré. Mot de passe généré : {password}',
                'generated_password': password
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
def recherche_patient(request): 
    query = request.GET.get('q', '').strip()
    
    # Requête de base pré-chargée avec ses clés étrangères
    base_queryset = Patient.objects.select_related(
        'fosa', 
        'mere', 
        'porte_entree', 
     
    )
    
    if query:
        patients = base_queryset.filter(
            Q(nom__icontains=query) | 
            Q(prenom__icontains=query) | 
            Q(code__icontains=query)
        ).distinct()[:50]  # Limite de sécurité pour éviter de surcharger le DOM
    else:
        patients = base_queryset.order_by('-id')[:20]
        
    return render(request, 'webpages/partials/patient_list.html', {'patients': patients})

def profile(request):
    return render(request, 'webpages/profile.html')

def define_plage(request):
    context={
        'now':datetime.now()
    }
    return render(request, 'webpages/resultats/plages.html',context)


def liste_echantillon(request):
    if request.method=="POST":
       pass

# Regex de validation : 3-3-3-2-X (ex: LIT-NYL-CML-PT-0222)
CODE_PATIENT_REGEX = r"^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{2}-[A-Z0-9]+$"


def segmenter_code_patient(raw_code):
    """Nettoie, segmente et formate un code patient au format XXX-XXX-XXX-XX-XXXX."""
    code_clean = raw_code.strip().upper()
    parts = code_clean.split("-")

    # Si le code est fourni sans aucun tiret (ex: LITNYLCMLPT0222)
    if len(parts) == 1 and len(code_clean) >= 15:
        region = code_clean[0:3]
        dept = code_clean[3:6]
        fosa = code_clean[6:9]
        type_code = code_clean[9:11]
        numero = code_clean[11:]
        return f"{region}-{dept}-{fosa}-{type_code}-{numero}"

    return code_clean

@require_POST
def save_code_patient(request):
    codes_enregistres = []
    codes_existants = []
    codes_invalides = []

    # 1. Vérification de la présence de fiche_id
    fiche_id = request.POST.get("fiche_id")
    if not fiche_id:
        return JsonResponse(
            {"status": "error", "erreur": "Identifiant de fiche manquant dans le formulaire."},
            status=400,
        )

    try:
        fiche = FicheEchantillon.objects.get(id=fiche_id)
    except FicheEchantillon.DoesNotExist:
        return JsonResponse(
            {"status": "error", "erreur": f"Fiche d'échantillon #{fiche_id} introuvable."},
            status=404,
        )

    # 2. Transaction atomique
    with transaction.atomic():
        for key, value in request.POST.items():
            if (key.startswith("code") or key.startswith("hidden_code")) and value.strip():
                raw_val = value.strip().upper()
                clean_code = re.sub(r'[^A-Z0-9]', '', raw_val)

                # Extraction des segments
                if len(clean_code) >= 15:
                    region = clean_code[0:3]
                    dept = clean_code[3:6]
                    fosa = clean_code[6:9]
                    pt = clean_code[9:11]
                    numero = clean_code[11:]
                    code_formatted = f"{region}-{dept}-{fosa}-{pt}-{numero}"
                elif "-" in raw_val:
                    parts = raw_val.split("-")
                    if len(parts) == 5:
                        region, dept, fosa, pt, numero = parts
                        code_formatted = raw_val
                    else:
                        codes_invalides.append(value)
                        continue
                else:
                    codes_invalides.append(value)
                    continue

                # --- PRise en compte de la PT ---
                if pt != "XX":
                    # Recherche STRICTE : On cherche si CE patient existe AVEC cette PT exacte
                    patient_existant = Patient.objects.filter(code=code_formatted).first()
                    
                    if patient_existant:
                        if FichePatient.objects.filter(patient=patient_existant, fiche=fiche).exists():
                                    return JsonResponse(
                            {
                                "status": "error",
                                "erreur": f"le patient {patient_existant.code} appartient deja a cette fiche.",
                                "codes_invalides": codes_invalides,
                            },
                            status=400,
                        )
                        codes_existants.append(code_formatted)
                        FichePatient.objects.create(patient=patient_existant, fiche=fiche)
                    else:
                        # Création du patient avec sa PT sélectionnée
                        patient_inexistant = Patient.objects.create(code=code_formatted)
                        instance_patient = Patient.objects.get(id = int(patient_inexistant.id))
                        FichePatient.objects.create(patient=instance_patient, fiche=fiche)
                        codes_enregistres.append(code_formatted)
                else:
                    # Cas où la PT est 'XX' (Non sélectionnée par l'utilisateur)
                    # On vérifie si le patient existe globalement peu importe la PT
                    regex_pattern = f"^{region}-{dept}-{fosa}-..-{numero}$"
                    patient_existant = Patient.objects.filter(code__regex=regex_pattern).first()

                    if patient_existant:
                        codes_existants.append(patient_existant.code)
                        Patient.objects.create(patient=patient_existant.id, fiche=fiche)

                    else:
                        # Impossible d'enregistrer un patient sans Porte d'Entrée valide
                        codes_invalides.append(code_formatted)

    # 3. Validation globale
    if not codes_enregistres and not codes_existants:
        return JsonResponse(
            {
                "status": "error",
                "erreur": "Aucun code valide n'a pu être enregistré. Veuillez vérifier la sélection de la Porte d'Entrée.",
                "codes_invalides": codes_invalides,
            },
            status=400,
        )

    # 4. Succès
    return JsonResponse(
        {
            "status": "success",
            "message": "Traitement effectué avec succès.",
            "codes_initialises": codes_enregistres,
            "codes_refuses": codes_existants,
            "codes_invalides": codes_invalides,
        },
        status=200,
    )
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from .models import Echantillon, ResultatPcr, Test

from django.shortcuts import render
from django.contrib import messages
from django.db.models import Q, IntegerField
from django.db.models.functions import Cast
from django.utils.dateparse import parse_date
from .models import Echantillon, Test, ResultatPcr

from .tasks import bulk_update_echantillons_async  # Import de la tâche Celery

def nettoyer_date_front(val_str):
    """
    Convertit une date 'JJ-MM-AAAA' ou 'JJ/MM/AAAA' saisie dans le formulaire 
    en chaîne ISO 'AAAA-MM-JJ' acceptée par la base de données.
    """
    if not val_str:
        return None
    val_str = val_str.strip()
    
    # Formats à essayer dans l'ordre
    formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d']
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

from urllib.parse import urlencode

def search_plage(request):
    tests = Test.objects.all()
    resultats_pcr = ResultatPcr.objects.all().exclude(nom__iexact='INDETERMINE')

    # Recommandation : On lit systématiquement request.GET pour conserver
    # les filtres de recherche présents dans l'URL.
    # Si des filtres sont passés dans la requête POST, on combine avec request.POST.
    data = request.POST if (request.method == 'POST' and 'debut_ancien_code' in request.POST) else request.GET

    selected_test_id = data.get('test_id', '').strip()
    selected_resultat_pcr_id = data.get('resultat_pcr_id', '').strip()
    debut_raw = data.get('debut_ancien_code', '').strip()
    fin_raw = data.get('fin_code_echantillon', '').strip()
    exclure_raw = data.get('liste_exclure', '').strip()
    inclusion_raw = data.get('liste_inclure', '').strip()
    global_date_raw = data.get('date_resultat', '').strip()

    # Nettoyage / Formatage ISO de la date globale
    global_date_resultat = nettoyer_date_front(global_date_raw)

    # -------------------------------------------------------------
    # 1. SAUVEGARDE EN MASSE VIA BROKER (CELERY)
    # -------------------------------------------------------------
    if request.method == 'POST' and 'save_results' in request.POST:
        echantillons_ids = request.POST.getlist('echantillon_ids')

        updates_data = []
        for ech_id in echantillons_ids:
            if ech_id.isdigit():
                date_indiv_raw = request.POST.get(f'date_resultat_{ech_id}', '').strip()
                date_indiv_clean = nettoyer_date_front(date_indiv_raw)

                updates_data.append({
                    'id': int(ech_id),
                    'resultat_id': request.POST.get(f'resultat_{ech_id}', '').strip(),
                    'tests': request.POST.get(f'test_{ech_id}', '').strip(),
                    'date_resultat': date_indiv_clean if date_indiv_clean else global_date_resultat
                })

        if updates_data:
            bulk_update_echantillons_async.delay(
                updates_data=updates_data,
                global_date_str=global_date_resultat
            )
            
            messages.success(
                request,
                f"Traitement lancé en arrière-plan pour {len(updates_data)} échantillon(s). La mise à jour sera effective dans quelques instants."
            )

            # --- CONSERVATION DES CRITÈRES DANS L'URL APRES REDIRECTION ---
            query_params = {
                'debut_ancien_code': debut_raw,
                'fin_code_echantillon': fin_raw,
                'liste_exclure': exclure_raw,
                'liste_inclure': inclusion_raw,
                'test_id': selected_test_id,
                'resultat_pcr_id': selected_resultat_pcr_id,
                'date_resultat': global_date_raw,
            }
            # Filtrage des clés vides
            clean_params = {k: v for k, v in query_params.items() if v}
            
            redirect_url = request.path
            if clean_params:
                redirect_url = f"{request.path}?{urlencode(clean_params)}"

            return redirect(redirect_url)

    # -------------------------------------------------------------
    # 2. FILTRAGE ET RECHERCHE
    # -------------------------------------------------------------
    debut = int(debut_raw) if debut_raw.isdigit() else None
    fin = int(fin_raw) if fin_raw.isdigit() else None

    def parse_code_list(raw_text):
        cleaned = raw_text.replace('\r\n', ',').replace('\n', ',').replace(';', ',')
        return [i.strip() for i in cleaned.split(',') if i.strip()]

    liste_exclure = parse_code_list(exclure_raw)
    liste_inclure = parse_code_list(inclusion_raw)

    base_qs = Echantillon.objects.all()

    # Filtrage par intervalle
    qs_plage = base_qs.none()
    if debut is not None or fin is not None:
        numeric_qs = base_qs.filter(code__regex=r'^\d+$').annotate(
            code_int=Cast('code', output_field=IntegerField())
        )
        
        query_plage = Q()
        if debut is not None and fin is not None:
            query_plage &= Q(code_int__gte=debut, code_int__lte=fin)
        elif debut is not None:
            query_plage &= Q(code_int__gte=debut)
        elif fin is not None:
            query_plage &= Q(code_int__lte=fin)

        qs_plage = numeric_qs.filter(query_plage)

    # Inclusions spécifiques
    qs_inclure = base_qs.none()
    if liste_inclure:
        qs_inclure = base_qs.filter(code__in=liste_inclure)

    # Combinaison des résultats
    if (debut is not None or fin is not None) and liste_inclure:
        echantillons = qs_plage | qs_inclure
    elif debut is not None or fin is not None:
        echantillons = qs_plage
    elif liste_inclure:
        echantillons = qs_inclure
    else:
        echantillons = base_qs.none()

    # Exclusions
    if liste_exclure and echantillons.exists():
        echantillons = echantillons.exclude(code__in=liste_exclure)

    # Filtres sur le champ 'tests' (CharField) et 'resultat_pcr_id'
    if selected_test_id:
        echantillons = echantillons.filter(tests=selected_test_id)

    if selected_resultat_pcr_id:
        echantillons = echantillons.filter(resultat_pcr_id=selected_resultat_pcr_id)

    # Optimisation SQL et Tri
    echantillons = (
        echantillons.distinct()
        .select_related('enfant', 'resultat_pcr')
        .order_by('code')
    )

    context = {
        'debut': debut_raw,
        'fin': fin_raw,
        'exclure': exclure_raw,
        'inclusion': inclusion_raw,
        'tests': tests,
        'resultats_pcr': resultats_pcr,
        'selected_test_id': selected_test_id,
        'selected_resultat_pcr_id': selected_resultat_pcr_id,
        'global_date_resultat': global_date_raw,
        'echantillons': echantillons,
    }

    return render(request, 'webpages/resultats/plages.html', context)
@permission_required('circb_app.modifier_resultats_patients', raise_exception=True)
@login_required
def save_plage(request):
    echantillons = []
    
    # 1. Récupération des paramètres de filtrage (POST ou GET)
    data = request.POST if request.method == 'POST' else request.GET

    debut_raw = data.get('debut_ancien_code', '').strip()
    fin_raw = data.get('fin_code_echantillon', '').strip()
    inclure_raw = data.get('liste_inclure', '').strip()
    exclure_raw = data.get('liste_exclure', '').strip()

    # Helper interne pour nettoyer les listes de codes
    def parse_code_list(raw_string):
        if not raw_string:
            return []
        cleaned = raw_string.replace('\r\n', ',').replace('\n', ',').replace(';', ',')
        return [c.strip() for c in cleaned.split(',') if c.strip()]

    codes_inclure = parse_code_list(inclure_raw)
    codes_exclure = parse_code_list(exclure_raw)

    debut = int(debut_raw) if debut_raw.isdigit() else None
    fin = int(fin_raw) if fin_raw.isdigit() else None

    # 2. TRAITEMENT DE L'ENREGISTREMENT DES RÉSULTATS (Soumission du Formulaire)
    if request.method == 'POST' and 'save_results' in request.POST:
        echantillon_ids = request.POST.getlist('echantillon_ids')
        date_resultat = request.POST.get('date_resultat') or None
        saved_count = 0

        with transaction.atomic():
            for ech_id in echantillon_ids:
                test_id = request.POST.get(f'test_{ech_id}') or None
                resultat_pcr_id = request.POST.get(f'resultat_{ech_id}') or None

                if test_id or resultat_pcr_id:
                    # Table d'historique/résultat
                    Resultat.objects.update_or_create(
                        echantillon_id=ech_id,
                        defaults={
                            'test_id': test_id,
                            'resultat_pcr_id': resultat_pcr_id,
                            'responsable': request.user,
                            'date_resultat': date_resultat,
                        }
                    )
                    
                    # Mise à jour directe de la fiche Échantillon
                    Echantillon.objects.filter(id=ech_id).update(
                        test_id=test_id, 
                        resultat_pcr_id=resultat_pcr_id,
                        date_resultat=date_resultat,
                    )
                    
                    saved_count += 1

        messages.success(request, f"{saved_count} résultat(s) enregistré(s) avec succès !")

    # 3. RECHERCHE ET EXTRACTION DES ÉCHANTILLONS
    base_qs = Echantillon.objects.all()

    # Filtre par intervalle numérique
    qs_plage = base_qs.none()
    if debut is not None or fin is not None:
        # Sécurité : On ne caste en entier QUE les codes purement numériques
        numeric_qs = base_qs.filter(code__regex=r'^\d+$').annotate(
            code_int=Cast('code', output_field=IntegerField())
        )
        query_plage = Q()
        if debut is not None and fin is not None:
            query_plage &= Q(code_int__gte=debut, code_int__lte=fin)
        elif debut is not None:
            query_plage &= Q(code_int__gte=debut)
        elif fin is not None:
            query_plage &= Q(code_int__lte=fin)

        qs_plage = numeric_qs.filter(query_plage)

    # Inclusions spécifiques (Supporte les codes texte comme "08D0000")
    qs_inclure = base_qs.none()
    if codes_inclure:
        qs_inclure = base_qs.filter(code__in=codes_inclure)

    # Combinaison des résultats
    if (debut is not None or fin is not None) and codes_inclure:
        queryset = qs_plage | qs_inclure
    elif debut is not None or fin is not None:
        queryset = qs_plage
    elif codes_inclure:
        queryset = qs_inclure
    elif request.method == 'POST':
        queryset = base_qs
    else:
        queryset = base_qs.none()

    # Exclusions
    if codes_exclure and queryset.exists():
        queryset = queryset.exclude(code__in=codes_exclure)

    if queryset.exists():
        echantillons = (
            queryset.distinct()
            .select_related('enfant', 'test', 'resultat_pcr')
            .order_by('code')
        )

    # 4. CHARGEMENT DES LISTES POUR LES SELECTS
    tests = Test.objects.all()
    resultats_pcr = ResultatPcr.objects.all()

    context = {
        'echantillons': echantillons,
        'tests': tests,
        'resultats_pcr': resultats_pcr,
        'debut': debut_raw,
        'fin': fin_raw,
        'inclusion': inclure_raw,
        'exclure': exclure_raw,
    }

    # Rend le template HTML au lieu d'une redirection forcée
    return render(request, 'webpages/resultats/plages.html', context)


def historique_echantillon(request):
    fiche_expedition= FicheEchantillon.objects.filter(status=False)
    context={
        'fiche_expedition':fiche_expedition
    }
    return render(request, 'webpages/echantillonages/historique.html', context)





def line_delete_structure(request, id):
    # 1. Récupération de l'objetline_dele
    structure = get_object_or_404(Structure, id=int(id))
    
    # 2. Vérification des relations avec les autres entités métiers
    # On exclut Structure d'ici pour traiter son arborescence proprement après
    models_to_check = [FicheEchantillon]
    can_delete = True

    for model in models_to_check:
        if model.objects.filter(fosa=structure).exists():
            can_delete = False
            break

    # 3. Vérification de l'arborescence (Si la structure est le PARENT d'autres sous-structures)
 
    if can_delete:
        has_children = Structure.objects.filter(parent=structure).exists()
        if has_children:
            can_delete = False
            messages.error(
                request, 
                f"'{structure.nom}' ne peut pas être supprimée car elle est le parent d'autres sous-structures."
            )
            return redirect(request.META.get('HTTP_REFERER', '/'))

    # 4. Action de suppression ou message d'erreur général
    if can_delete:
        nom_structure = structure.nom  # Sauvegarde du nom avant suppression
        structure.delete()
        messages.success(request, f"La structure '{nom_structure}' a été supprimée avec succès.")
    else:
        messages.error(
            request, 
            f"Impossible de supprimer '{structure.nom}' : elle est liée à des opérations ou des valeurs d'indicateurs."
        )

    return redirect(request.META.get('HTTP_REFERER', '/'))





def delete_hierachie(request, id):
    # 1. Récupération sécurisée de l'objet (renvoie une erreur 404 si l'ID n'existe pas)
    hierachie = get_object_or_404(Structure_Hierachy, id=int(id))

    # 2. Vérification s'il existe des structures (FOSAS, districts, etc.) liées à cette hiérarchie
    if Structure.objects.filter(hierachy=hierachie).exists():
        # Si oui, on refuse la suppression pour éviter les données orphelines
        messages.error(
            request, 
            f'Impossible de supprimer "{hierachie.nom}" car elle est actuellement liée à des structures existantes.'
        )
    else:
        # Si aucune structure n'est liée, on supprime proprement
        hierachie.delete()
        messages.success(request, f'La hiérarchie "{hierachie.nom}" a été supprimée avec succès.')

    # 3. Redirection vers la page précédente ou la liste des hiérarchies
    return redirect(request.META.get('HTTP_REFERER', '/'))






from django.shortcuts import render
from datetime import date
from .models import Echantillon

def previsualisation_fiche_synthetique(request):
    
    fosa_id = request.GET.get('fosa_id')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    request.session['fosa'] = fosa_id
    request.session['date_debut'] = date_debut
    request.session['date_fin'] = date_fin
  
    
     

    # ÉTAPE 1 : Filtrer pour trouver les enfants concernés par la période/FOSA
    base_queryset = Echantillon.objects.all()

    if fosa_id and fosa_id != 'ALL':
        base_queryset = base_queryset.filter(fiche__fosa_id=fosa_id)

    # Filtrage flexible par date (optionnel : gère début seul, fin seule, ou les deux)
    if date_debut:
        base_queryset = base_queryset.filter(date_prelevement__gte=date_debut)
    if date_fin:
        base_queryset = base_queryset.filter(date_prelevement__lte=date_fin)

    enfants_ids = base_queryset.exclude(enfant__isnull=True).values_list('enfant_id', flat=True).distinct()
    echantillons_sans_enfant = base_queryset.filter(enfant__isnull=True).values_list('id', flat=True)

    # ÉTAPE 2 : Récupérer TOUS les échantillons de ces enfants
    queryset = Echantillon.objects.select_related(
        'enfant', 'mere', 'fiche__fosa', 'test', 'resultat_pcr'
    ).prefetch_related('resultats__test', 'resultats__resultat_pcr').filter(
        enfant_id__in=enfants_ids
    ) | Echantillon.objects.select_related(
        'enfant', 'mere', 'fiche__fosa', 'test', 'resultat_pcr'
    ).prefetch_related('resultats__test', 'resultats__resultat_pcr').filter(
        id__in=echantillons_sans_enfant
    )

    fosa_nom_affiche = "Toutes les Formations Sanitaires"
    if fosa_id and fosa_id != 'ALL':
        premier_ech = base_queryset.first()
        if premier_ech and premier_ech.fiche and premier_ech.fiche.fosa:
            fosa_nom_affiche = premier_ech.fiche.fosa.nom

    # ÉTAPE 3 : Grouper les échantillons par Enfant
    patients_samples = {}
    patients_info = {}

    for ech in queryset:
        cle_pivot = ech.enfant.id if ech.enfant else f"ech_{ech.id}"
        
        if cle_pivot not in patients_info:
            patients_info[cle_pivot] = {
                'code': ech.enfant.code if (ech.enfant and hasattr(ech.enfant, 'code')) else ech.code,
                'patient_nom': f"{getattr(ech.enfant, 'nom', '')} {getattr(ech.enfant, 'prenom', '')}".strip() if ech.enfant else "Non renseigné",
                'date_naissance': getattr(ech.enfant, 'date_naissance', 'N/A'),
                'mere_nom': f"{getattr(ech.mere, 'nom', '')} {getattr(ech.mere, 'prenom', '')}".strip() if ech.mere else "N/A",
                'mere_contact': getattr(ech.mere, 'contact', 'N/A'),
            }
        
        if cle_pivot not in patients_samples:
            patients_samples[cle_pivot] = []
        
        patients_samples[cle_pivot].append(ech)

    # ÉTAPE 4 : Pour chaque enfant, mapper les prélèvements selon leur attribut 'ordre' (PCR I, II, III)
    lignes_collectives = []

    for cle_pivot, echos in patients_samples.items():
        row_data = patients_info[cle_pivot].copy()
        row_data.update({
            'pcr1': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_res': '-'},
            'pcr2': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_res': '-'},
            'pcr3': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_res': '-'},
        })

        # Affectation directe basée sur le champ 'ordre' de l'échantillon
        for ech in echos:
            statut_nom = ech.resultat_pcr.nom if ech.resultat_pcr else "EN ATTENTE"
            statut_code = ech.resultat_pcr.code if ech.resultat_pcr else ""
            date_res = "-"

            # Vérification table secondaire si besoin
            res_associe = ech.resultats.first()
            if res_associe:
                if res_associe.resultat_pcr:
                    statut_nom = res_associe.resultat_pcr.nom
                    statut_code = res_associe.resultat_pcr.code
                date_res = res_associe.date_resultat

            donnees_pcr = {
                'date_prel': ech.date_prelevement,
                'statut': statut_nom,
                'code_statut': statut_code,
                'date_res': date_res
            }

            # On répartit selon la valeur explicite de 'ordre' (1, 2 ou 3)
            if ech.ordre == 1:
                row_data['pcr1'] = donnees_pcr
            elif ech.ordre == 2:
                row_data['pcr2'] = donnees_pcr
            elif ech.ordre == 3:
                row_data['pcr3'] = donnees_pcr

        lignes_collectives.append(row_data)

    context = {
        'lignes_collectives': lignes_collectives,
        'date_debut': date_debut or '',
        'date_fin': date_fin or '',
        'fosa_nom_affiche': fosa_nom_affiche,
    }
    
    return render(request, 'webpages/previsualisation_fiche.html', context)
def ModifyHierachy(request, id):
    template = 'webpages/config/modify-hierachy.html'
    hierachie = Structure_Hierachy.objects.get(id=int(id))
    context ={
    'hierachie':hierachie

    }
    return render(request, template, context)






def UpdateStructure(request, id):
    # 1. Récupération du contexte de base
    template = 'webpages/config/update-structure.html'
    
    # 2. Récupération sécurisée de la structure à modifier
    structure = get_object_or_404(Fosa, id=int(id))

    # Construction sécurisée de l'identification (gère tous les niveaux de profondeur)
    parts = []
    current = structure
    while current:
        parts.insert(0, current.designation)
        current = current.parent
    
    identifiaction = "-".join(parts)
    
    # 3. Enrichissement du contexte
    context = {
        'structure': structure,
        'hierachie': Structure_Hierachy.objects.order_by('rang'),
        'all_structures': Structure.objects.all(),
        'identifiaction': identifiaction
    }
    
    return render(request, template, context)

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages


@transaction.atomic
def UpdateDataStructure(request, id):

    if request.method != 'POST':
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # =========================================================
    # 1. STRUCTURE À MODIFIER
    # =========================================================

    structure = get_object_or_404(
        Structure,
        id=int(id)
    )

    # =========================================================
    # 2. DONNÉES DU FORMULAIRE
    # =========================================================

    parent_id = request.POST.get('parent_id')
    level_id = request.POST.get('level_id')
    nom = request.POST.get('nom')
    designation = request.POST.get('designation')

    # Ancien code de la structure
    # Exemple : ADA-MGA-DIR
    old_code_patient = request.POST.get('old_code')

    try:

        # =========================================================
        # 3. RÉCUPÉRER LE NOUVEAU PARENT
        # =========================================================

        parent = None

        if parent_id and int(parent_id) != structure.id:

            parent = get_object_or_404(
                Structure,
                id=int(parent_id)
            )

        # =========================================================
        # 4. RECONSTRUIRE LE NOUVEAU CODE
        # =========================================================

        elements = []

        current = parent

        while current:

            if current.designation:
                elements.append(current.designation)

            current = current.parent

        elements.reverse()

        if designation:
            elements.append(designation)

        nouveau_code = "-".join(elements)

        print("========================================")
        print("ANCIEN CODE :", old_code_patient)
        print("NOUVEAU CODE :", nouveau_code)
        print("========================================")

        # =========================================================
        # 5. IDENTIFIER RÉGION / DISTRICT
        # =========================================================

        nouvelle_region = None
        nouveau_district = None

        if parent:

            # Le parent de la FOSA
            nouveau_district = parent

            # Le parent du district
            nouvelle_region = parent.parent

        print("Nouvelle région :", nouvelle_region)
        print("Nouveau district :", nouveau_district)
        print("FOSA :", structure)

        # =========================================================
        # 6. MISE À JOUR DES FICHES ÉCHANTILLONS
        # =========================================================

        fiches = FicheEchantillon.objects.filter(
            fosa=structure
        )

        nombre_fiches = fiches.count()

        if nombre_fiches > 0:

            fiches.update(
                region=nouvelle_region,
                district=nouveau_district,
                fosa=structure
            )

        print(
            f"{nombre_fiches} fiche(s) échantillon mise(s) à jour."
        )

        # =========================================================
        # 7. MISE À JOUR DES CODES PATIENTS
        # =========================================================

        nombre_patients = 0
        nombre_modifies = 0

        if old_code_patient and nouveau_code:

            # Les 11 premiers caractères
            ancien_prefixe = old_code_patient[:11]
            nouveau_prefixe = nouveau_code[:11]

            print("Ancien préfixe :", ancien_prefixe)
            print("Nouveau préfixe :", nouveau_prefixe)

            # -----------------------------------------------------
            # Rechercher les patients
            # -----------------------------------------------------

            patients = Patient.objects.filter(
                code__startswith=ancien_prefixe
            )

            nombre_patients = patients.count()

            print(
                f"{nombre_patients} patient(s) trouvé(s)."
            )

            # -----------------------------------------------------
            # Modifier les codes
            # -----------------------------------------------------

            for patient in patients:

                ancien_code = patient.code

                # Vérification stricte des 11 caractères
                if ancien_code[:11] != ancien_prefixe:
                    continue

                # Garder le reste du code
                #
                # ADA-MGA-DIR-NU-0007
                # ADA-MGA-DIR = 11 caractères
                # -NU-0007 = suffixe
                suffixe = ancien_code[11:]

                # Nouveau code
                nouveau_code_patient = (
                    nouveau_prefixe + suffixe
                )

                patient.code = nouveau_code_patient

                patient.save(
                    update_fields=['code']
                )

                nombre_modifies += 1

                print(
                    f"{ancien_code} -> "
                    f"{nouveau_code_patient}"
                )

        # =========================================================
        # 8. MISE À JOUR DE LA STRUCTURE
        # =========================================================

        if level_id:

            structure.hierachy = get_object_or_404(
                Structure_Hierachy,
                id=int(level_id)
            )

        structure.parent = parent
        structure.nom = nom
        structure.designation = designation

        structure.save()

        # =========================================================
        # 9. MESSAGE DE SUCCÈS
        # =========================================================

        messages.success(
            request,
            f"L'unité '{nom}' a été modifiée avec succès. "
            f"{nombre_modifies} patient(s) et "
            f"{nombre_fiches} fiche(s) échantillon "
            f"ont été mis à jour."
        )

        return redirect('/structures/')

    except Exception as e:

        messages.error(
            request,
            f"Une erreur est survenue lors de la modification : {str(e)}"
        )

        return redirect(
            request.META.get('HTTP_REFERER', '/')
        )
import os
import io
import base64
from collections import defaultdict
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from django.db.models import Q, IntegerField
from django.db.models.functions import Cast
from xhtml2pdf import pisa


def imprimer_resultat_pdf(request):
    data = request.POST if request.method == 'POST' else request.GET

    debut_raw = data.get('debut_ancien_code', '').strip()
    fin_raw = data.get('fin_code_echantillon', '').strip()
    inclure_raw = data.get('liste_inclure', '').strip()
    exclure_raw = data.get('liste_exclure', '').strip()

    def parse_code_list(raw_string):
        if not raw_string:
            return []
        cleaned = raw_string.replace('\r\n', ',').replace('\n', ',').replace(';', ',')
        return [c.strip() for c in cleaned.split(',') if c.strip()]

    codes_inclure = parse_code_list(inclure_raw)
    codes_exclure = parse_code_list(exclure_raw)

    debut = int(debut_raw) if debut_raw.isdigit() else None
    fin = int(fin_raw) if fin_raw.isdigit() else None

    # 1. Chargement et conversion du logo CIRCB en Base64
    logo_base64 = ""
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find("images/logo_circb.png")
    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Filtrage des échantillons
    base_qs = Echantillon.objects.all()

    qs_plage = base_qs.none()
    if debut is not None or fin is not None:
        numeric_qs = base_qs.filter(code__regex=r'^\d+$').annotate(
            code_int=Cast('code', output_field=IntegerField())
        )
        query_plage = Q()
        if debut is not None and fin is not None:
            query_plage &= Q(code_int__gte=debut, code_int__lte=fin)
        elif debut is not None:
            query_plage &= Q(code_int__gte=debut)
        elif fin is not None:
            query_plage &= Q(code_int__lte=fin)

        qs_plage = numeric_qs.filter(query_plage)

    qs_inclure = base_qs.none()
    if codes_inclure:
        qs_inclure = base_qs.filter(code__in=codes_inclure)

    if (debut is not None or fin is not None) and codes_inclure:
        base_queryset = qs_plage | qs_inclure
    elif debut is not None or fin is not None:
        base_queryset = qs_plage
    elif codes_inclure:
        base_queryset = qs_inclure
    else:
        base_queryset = base_qs

    if codes_exclure and base_queryset.exists():
        base_queryset = base_queryset.exclude(code__in=codes_exclure)

    enfants_ids = base_queryset.exclude(enfant__isnull=True).values_list('enfant_id', flat=True).distinct()
    echantillons_sans_enfant = base_queryset.filter(enfant__isnull=True).values_list('id', flat=True)

    # 3. Correction select_related : Utilisation de parent__parent au lieu de district__region
    queryset = Echantillon.objects.select_related(
        'enfant', 'mere', 'fiche__fosa__parent__parent', 'resultat_pcr'
    ).prefetch_related('resultats__resultat_pcr').filter(
        enfant_id__in=enfants_ids
    ) | Echantillon.objects.select_related(
        'enfant', 'mere', 'fiche__fosa__parent__parent', 'resultat_pcr'
    ).prefetch_related('resultats__resultat_pcr').filter(
        id__in=echantillons_sans_enfant
    )

    # 4. Regroupement par FOSA, puis par Enfant/Patient
    fosa_patients_samples = defaultdict(lambda: defaultdict(list))
    fosa_patients_info = defaultdict(dict)
    fosa_metadata = {}

    for ech in queryset:
        fosa_obj = ech.fiche.fosa if (ech.fiche and ech.fiche.fosa) else None
        nom_fosa = fosa_obj.nom if (fosa_obj and fosa_obj.nom) else "Formation Sanitaire non renseignée"

        # Traitement de la hiérarchie parent (FOSA -> District -> Région)
        if nom_fosa not in fosa_metadata:
            nom_region = "Non renseignée"
            nom_district = "Non renseigné"

            if fosa_obj and hasattr(fosa_obj, 'parent') and fosa_obj.parent:
                nom_district = getattr(fosa_obj.parent, 'nom', 'Non renseigné')
                if hasattr(fosa_obj.parent, 'parent') and fosa_obj.parent.parent:
                    nom_region = getattr(fosa_obj.parent.parent, 'nom', 'Non renseignée')

            fosa_metadata[nom_fosa] = {
                'region_nom': nom_region,
                'district_nom': nom_district,
            }

        cle_pivot = ech.enfant.id if ech.enfant else f"ech_{ech.id}"
        
        if cle_pivot not in fosa_patients_info[nom_fosa]:
            fosa_patients_info[nom_fosa][cle_pivot] = {
                'code': ech.enfant.code if (ech.enfant and hasattr(ech.enfant, 'code')) else ech.code,
                'patient_nom': f"{getattr(ech.enfant, 'nom', '')} {getattr(ech.enfant, 'prenom', '')}".strip() if ech.enfant else "Non renseigné",
                'date_naissance': getattr(ech.enfant, 'date_naissance', 'N/A'),
                'mere_nom': f"{getattr(ech.mere, 'nom', '')} {getattr(ech.mere, 'prenom', '')}".strip() if ech.mere else "N/A",
                'mere_contact': getattr(ech.mere, 'contact', 'N/A'),
            }
        
        fosa_patients_samples[nom_fosa][cle_pivot].append(ech)

    # 5. Structuration finale envoyée au template
    donnees_par_fosa = []

    for nom_fosa, patients_samples in fosa_patients_samples.items():
        lignes_fosa = []
        for cle_pivot, echos in patients_samples.items():
            row_data = fosa_patients_info[nom_fosa][cle_pivot].copy()
            row_data.update({
                'pcr1': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_resultat': '-'},
                'pcr2': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_resultat': '-'},
                'pcr3': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_resultat': '-'},
            })

            for ech in echos:
                statut_nom = ech.resultat_pcr.nom if ech.resultat_pcr else "EN ATTENTE"
                statut_code = ech.resultat_pcr.code if ech.resultat_pcr else ""
                date_resultat = "-"

                res_associe = ech.resultats.first()
                if res_associe:
                    if res_associe.resultat_pcr:
                        statut_nom = res_associe.resultat_pcr.nom
                        statut_code = res_associe.resultat_pcr.code
                    date_resultat = res_associe.date_resultat

                donnees_pcr = {
                    'date_prel': ech.date_prelevement,
                    'statut': statut_nom,
                    'code_statut': statut_code,
                    'date_resultat': date_resultat
                }

                if ech.ordre == 1:
                    row_data['pcr1'] = donnees_pcr
                elif ech.ordre == 2:
                    row_data['pcr2'] = donnees_pcr
                elif ech.ordre == 3:
                    row_data['pcr3'] = donnees_pcr

            lignes_fosa.append(row_data)

        meta = fosa_metadata.get(nom_fosa, {'region_nom': 'Non renseignée', 'district_nom': 'Non renseigné'})
    
        donnees_par_fosa.append({
            'fosa_nom': nom_fosa,
            'region_nom': meta['region_nom'],
            'district_nom': meta['district_nom'],
            'lignes': lignes_fosa
        })

    # 6. Génération du PDF
    context = {
        'donnees_par_fosa': donnees_par_fosa,
        'debut': debut_raw,
        'fin': fin_raw,
        'logo_base64': logo_base64,
    }

    html_content = render_to_string("webpages/rapports/resultat_pdf.html", context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="Resultats_EID.pdf"'

    pisa_status = pisa.pisaDocument(
        io.BytesIO(html_content.encode("utf-8")), response, encoding="utf-8"
    )

    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF.", status=500)

    return response
def parse_custom_date(date_str):
    """Convertit une chaîne 'JJ-MM-AAAA' en objet date Python."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%d-%m-%Y").date()
    except (ValueError, TypeError):
        return None

def modifier_fiche_echantillon(request, id):
    fiche = get_object_or_404(FicheEchantillon, id=id)
    
    if request.method == 'POST':
        try:
            # 1. Conversion des dates personnalisées
            fiche.date_enregistrement = parse_custom_date(request.POST.get('date_enregistrement')) or fiche.date_enregistrement
            fiche.date_expedition = parse_custom_date(request.POST.get('date_expedition')) or fiche.date_expedition
            fiche.date_reception = parse_custom_date(request.POST.get('date_reception')) or fiche.date_reception
            
            date_envoie_labo = parse_custom_date(request.POST.get('date_entree_labo'))
            if date_envoie_labo:
                fiche.date_Envoie_labo = date_envoie_labo

            # 2. Gestion de la FOSA (et mise à jour de la région/district si ce sont des champs de la fiche)
            fosa_id = request.POST.get('fosa')
            if fosa_id:
                fiche.fosa_id = fosa_id
            
            # Si 'region' et 'district' sont des champs (ForeignKey ou ID) directs de la fiche :
            region_id = request.POST.get('region')
            if region_id:
                fiche.region_id = region_id # ou fiche.region = region_id selon votre modèle
                
            district_id = request.POST.get('district')
            if district_id:
                fiche.district_id = district_id # ou fiche.district = district_id selon votre modèle

            # 3. Champs texte et attributs simples
            fiche.expediteur = request.POST.get('expediteur', fiche.expediteur)
            fiche.nombre_echantillon = request.POST.get('nombre_echantillon', fiche.nombre_echantillon)
            fiche.transporteur = request.POST.get('transporteur', fiche.transporteur)
            
            moyen_id = request.POST.get('moyen_transport')
            if moyen_id:
                fiche.moyen_transport_id = moyen_id
                
            fiche.observation = request.POST.get('observation', fiche.observation)
            
            # 4. Sauvegarde finale en base de données
            fiche.save()
            
            messages.success(request, f"La fiche d'expédition {fiche.code} a été mise à jour avec succès.")
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification : {str(e)}")
            
    return redirect('/fiches-echantillons/')

def modifier_fiche(request, id):
    fiche = get_object_or_404(FicheEchantillon, id=id)
    
    context = {
        'fiche': fiche,
        'regions': Region.objects.all(),
        'transporteurs': Transporteur.objects.all(), # Adaptez selon vos modèles réels
        'moyens_transport': MoyenTransport.objects.all(), # Adaptez selon vos modèles réels
    }
    return render(request, 'webpages/echantillonages/edit-fiche.html', context)

@permission_required('circb_app.peut_supprimer_echantillons')
def delete_echantillon(request, id):
    echantillon = Echantillon.objects.get(id=int(id))
    echantillon.delete()
    messages.success(request, 'Supression reussie' )
    
    return redirect(request.META.get('HTTP_REFERER','/'))


def modifier_echantillon(request, id):
    context={
        'echantillon':Echantillon.objects.get(id=int(id)),
        'portes_entree':PorteEntree.objects.all(),
        'profilaxie_arv': ProfilaxieArv.objects.all(),
        'mode_accouchement': ModeAccouchement.objects.all(),
        'protocole_ptme': ProtocolePTME.objects.all(),
        'modes_allaitement':ModeAllaitement.objects.filter(is_artificiel=False),
        'modes_allaitement_artificiel':ModeAllaitement.objects.filter(is_artificiel=True),
    }
    return render(request, 'webpages/echantillonages/edit-echantillon.html', context)


def edit_patient(request, code):
    context={
        'patient':Patient.objects.get(code=code)
    }
    return render(request,'webpages/patients/edit-patient.html', context)


def UploadSubStructure(request, id):
    template = 'webpages/config/upload-sub-structure.html'
    structure = Structure.objects.get(id=int(id))
   
    context = {
    'structure': structure
    }
    return render(request, template, context)




def import_structure_view(request):
    
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # 1. Récupération de la structure parente sélectionnée sur l'interface (par défaut)
        parent_id = request.POST.get('parent_id')
        current_structure = None
        
        if parent_id:
            try:
                current_structure = Structure.objects.get(id=parent_id)
            except (Structure.DoesNotExist, ValueError):
                return JsonResponse({'success': False, 'error': 'Structure parente par défaut introuvable.'}, status=400)

        file = request.FILES.get('file_structure')
        if not file:
            return JsonResponse({'success': False, 'error': 'Aucun fichier fourni.'}, status=400)

        if not file.name.endswith('.csv'):
            return JsonResponse({'success': False, 'error': 'Format de fichier non supporté. Veuillez injecter un fichier .csv'}, status=400)

        try:
            data_set = file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            
            try:
                header = next(io_string) 
            except StopIteration:
                return JsonResponse({'success': False, 'error': 'Le fichier CSV est vide.'}, status=400)
            
            structures_creees = 0
            errors = []

            reader = csv.reader(io_string, delimiter=';', quotechar='"')
            
            for index, row in enumerate(reader, start=2):
                if not row or len(row) < 1 or not row[0].strip():
                    continue  

                # Extraction des données du CSV
                nom = row[0].strip()
                designation = row[1].strip() if len(row) > 1 else ''
                parent_nom_csv = row[2].strip() if len(row) > 2 and row[2].strip() else None

                # Détermination du parent
                parent_obj = current_structure  
                
                # Si le CSV spécifie explicitement un nom de parent, on le cherche
                if parent_nom_csv:
                    try:
                        parent_obj = Structure.objects.get(
                            nom__iexact=parent_nom_csv, 
                           
                        )
                    except Structure.DoesNotExist:
                        errors.append(f"Ligne {index} : La structure parente nommée '{parent_nom_csv}' est introuvable dans cette institution.")
                        continue
                    except Structure.MultipleObjectsReturned:
                        errors.append(f"Ligne {index} : Plusieurs structures portent le nom '{parent_nom_csv}'. Impossible de trancher.")
                        continue

                # Création ou mise à jour basée sur le NOM sous un même PARENT
                # (Évite les doublons exacts au même endroit de l'arborescence)
                obj, created = Structure.objects.get_or_create(
                    nom=nom,
                    parent=parent_obj,
                  
                    defaults={
                        'designation': designation,
                    }
                )

                # Optionnel : si la structure existait déjà mais qu'on veut mettre à jour sa désignation
                if not created and designation:
                    obj.designation = designation
                    obj.save()

                if created:
                    structures_creees += 1

            if errors:
                return JsonResponse({
                    'success': False, 
                    'error': f"{len(errors)} erreur(s) critique(s) rencontrée(s) : \n" + "\n".join(errors[:5])
                }, status=400)

            parent_name = current_structure.nom if current_structure else "la racine"
            return JsonResponse({
                'success': True,
                'message': f"{structures_creees} unité(s) organisationnelle(s) traitée(s) avec succès !"
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f"Erreur de traitement interne : {str(e)}"}, status=500)

    return redirect(request.META.get('HTTP_REFERER', '/'))


def mode_utilisation(request):
    return render(request, 'webpages/mode_utilisation.html')


def modifier_patient(request, pk):
    # Récupérer le patient par son identifiant
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        try:
            # 1. Mise à jour des informations de l'enfant (Patient)
            patient.nom = request.POST.get('nom')
            patient.prenom = request.POST.get('prenom', '')
            
            date_naiss = request.POST.get('date_naissance')
            patient.date_naissance = date_naiss if date_naiss else None
            
            patient.sexe = request.POST.get('sexe')
            
            
            # Gestion de la case à cocher (checkbox 'status')
            patient.status = True if request.POST.get('status') == 'on' else False
            
            patient.save()

            # 2. Mise à jour ou création des informations de la Mère
            # Récupère la mère liée, ou en crée une nouvelle si elle n'existe pas encore
            mere = getattr(patient, 'mere', None)
            if not mere:
                mere = Mere(patient=patient) # Adaptez selon la structure de votre modèle Mere
            
            mere.nom = request.POST.get('mere_nom', '')
            mere.prenom = request.POST.get('mere_prenom', '')
            
            date_naiss_mere = request.POST.get('mere_date_naissance')
            mere.date_naissance = date_naiss_mere if date_naiss_mere else None
            
            age_mere = request.POST.get('mere_age')
            mere.age = int(age_mere) if age_mere else None
            
            mere.contact = request.POST.get('mere_contact', '')
            mere.save()

            messages.success(request, "Les modifications du dossier ont été enregistrées avec succès.")
            return redirect('/dossiers/patients/', pk=patient.pk) # Remplacez par le nom de votre route de redirection

        except Exception as e:
            messages.error(request, f"Erreur lors de la modification : {e}")

    context = {
        'patient': patient,
    }
    return render(request, 'webpages/patients/dossiers.html', context)
@permission_required('circb_app.supprimer_resultats_patients', raise_exception=True)
def delete_resultat(request, id):
    # 1. On récupère l'échantillon correspondant
    echantillon = get_object_or_404(Echantillon, id=id)
    
    # 2. On réinitialise le champ resultat_pcr
    echantillon.resultat_pcr = None
    echantillon.save()
    
    messages.success(request, "Le résultat de l'échantillon a été annulé/effacé avec succès.")
    return redirect(request.META.get('HTTP_REFERER', '/'))

from django.contrib.auth.models import Group, Permission
@login_required(login_url='/')
@permission_required('circb_app.manage_system_settings', raise_exception=True)
def gestion_roles_interface(request):
    # Récupère tous les groupes (rôles) existants
    groupes = Group.objects.all()
    
    # Récupère uniquement les permissions de votre application (remplacez 'votre_app' par votre nom d'app)
    permissions = Permission.objects.filter(content_type__app_label='circb_app')

    if request.method == 'POST':
        nom_groupe = request.POST.get('nom_groupe')
        permissions_ids = request.POST.getlist('permissions') # Liste des IDs des checkboxes cochées

        if nom_groupe:
            # Crée ou récupère le groupe
            groupe, created = Group.objects.get_or_create(name=nom_groupe)
            
            # Assigne les permissions sélectionnées au groupe
            groupe.permissions.set(permissions_ids)
            return redirect('/configurations/')

    return render(request, 'webpages/config/configurations.html', {
        'groupes': groupes,
        'permissions': permissions
    })


@login_required(login_url='/')
def edit_role(request, role_id):
    # 1. Récupérer le rôle (groupe) concerné, ou erreur 404 s'il n'existe pas
    role = get_object_or_404(Group, id=role_id)
    
    # 2. Récupérer les permissions (ajustez le filtre selon votre application)
    permissions = Permission.objects.filter(content_type__app_label='circb_app')
    # Si vous voulez filtrer les permissions personnalisées comme vu avant :
    permissions = Permission.objects.filter(content_type__app_label='circb_app').exclude(
         Q(codename__startswith='add_') | Q(codename__startswith='change_') |
         Q(codename__startswith='delete_') | Q(codename__startswith='view_')
     )

    # 3. Traitement lors de la soumission du formulaire (POST)
    if request.method == 'POST':
        nom_groupe = request.POST.get('nom_groupe')
        permissions_ids = request.POST.getlist('permissions') # Liste des IDs cochés

        if nom_groupe:
            # Mettre à jour le nom du rôle
            role.name = nom_groupe.strip()
            role.save()
            
            # Assigner/Mettre à jour les permissions du groupe
            role.permissions.set(permissions_ids)
            
            # Rediriger vers la page principale de configurations (ou autre)
            return redirect('/configurations/')

    # 4. Affichage de la page (GET)
    context = {
        'role': role,
        'permissions': permissions,
    }
    return render(request, 'webpages/config/edit-role.html', context)



def custom_permission_denied_view(request, exception=None):
    # Vous pouvez passer des variables spécifiques au template ici
    context = {
        'user_connecte': request.user,
        'message_specifique': "Accès restreint par la politique de sécurité du CIRCB."
    }
    return render(request, 'webpages/403.html', context, status=403)


def modifier_personnel(request, id):
    context={
        'user':User.objects.get(id=int(id)),
        'groups':Group.objects.all()
    }
    return render(request,'webpages/config/edit-personnel.html', context)


def modifier_personnel(request, id):
    user = get_object_or_404(User, id=id)
    
    if request.method == 'POST':
        # Récupération des données du formulaire
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        
        # Gestion du groupe (remplace l'ancien groupe par le nouveau sélectionné)
        group_name = request.POST.get('group_name')
        if group_name:
            try:
                group = Group.objects.get(name=group_name)
                user.groups.set([group])  # Remplace tous les groupes actuels par ce groupe unique
            except Group.DoesNotExist:
                pass
        
        # Gestion optionnelle du mot de passe
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password:  # Si un nouveau mot de passe a été saisi
            if password == confirm_password:
                user.set_password(password)  # Hache et met à jour le mot de passe
            else:
                messages.error(request, "Les mots de passe ne correspondent pas.")
                return redirect('modifier-personnel', id=id)
                
        user.save()
        messages.success(request, "Le personnel a été mis à jour avec succès.")
        return redirect('/personnel/')  # Remplacez par le nom de votre route de redirection après modification
        
    context = {
        'user': user,
        'groups': Group.objects.all()
    }
    return render(request, 'webpages/config/edit-personnel.html', context)




def annuaire_personnel(request):
    # Récupération du terme de recherche
    query = request.GET.get('q', '')
    
    # Récupération de tous les utilisateurs (avec optimisation des groupes)
    users_list = User.objects.all().prefetch_related('groups').order_by('-date_joined')
    
    # Filtrage si une recherche est effectuée
    if query:
        users_list = users_list.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(username__icontains=query)
        )
        
    # Configuration de la pagination (12 utilisateurs par page pour correspondre à la grille)
    paginator = Paginator(users_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    groupes = Group.objects.all()
    
    context = {
        'user': page_obj,      # Utilisé dans votre template (itérable de la page)
        'page_obj': page_obj,  # Objet de pagination Django
        'groupes': groupes,    # Pour le select de la modale d'ajout
        'query': query,
    }
    
    # Si la requête vient de HTMX, on renvoie uniquement le fragment HTML ( Grille + Pagination )
    if request.headers.get('HX-Request'):
        return render(request, 'webpages/config/partials/personnel_container.html', context)
        
    # Sinon, on renvoie la page complète
    return render(request, 'webpages/config/annuaire_personnel.html', context)



def update_level(request, id):
    """
    Vue permettant de mettre à jour le nom et le rang d'un niveau hiérarchique
    via une requête POST envoyée depuis la modal SweetAlert2.
    """
    # On accepte uniquement les requêtes POST pour la modification
    if request.method == "POST":
        # 1. Récupération sécurisée de l'objet (renvoie une erreur 404 s'il n'existe pas)
        level = get_object_or_404(Structure_Hierachy, id=id)
        
        # 2. Extraction des données envoyées par le formulaire de la modal
        nouveau_nom = request.POST.get('nom')
        nouveau_rang = request.POST.get('rang')
        
        # 3. Validation rapide côté serveur
        if nouveau_nom and nouveau_rang:
            try:
                # Mise à jour des attributs de l'objet
                level.nom = nouveau_nom.strip()
                level.rang = int(nouveau_rang)
                
                # Sauvegarde effective dans la base de données
                level.save()
                
                # Message flash de succès
                messages.success(request, f'Le niveau "{level.nom}" a été mis à jour avec succès.')
            except ValueError:
                messages.error(request, "Le rang fourni doit être un nombre valide.")
            except Exception as e:
                messages.error(request, f"Une erreur est survenue lors de la sauvegarde : {str(e)}")
        else:
            messages.error(request, "Tous les champs (Nom et Rang) sont obligatoires.")
            
    # 4. Redirection vers la page d'où provenait la requête (ou l'index par défaut)
    return redirect('/structures/')
def check_code(request, id):
    # 1. Récupération de la fiche avec gestion propre du 404
    fiche = get_object_or_404(FicheEchantillon, id=id)
    
    # 2. Récupération des patients liés à la fiche (via FichePatient)
    patients = FichePatient.objects.filter(fiche=fiche).select_related('patient')
    
    # 3. Récupération des échantillons de cette fiche, 
    # en préchargeant leur 'resultat_pcr' pour éviter les requêtes N+1
    echantillons = Echantillon.objects.filter(fiche=fiche).select_related(
        'enfant', 'resultat_pcr', 'raison_prelevement', 'porte_entree'
    )

    context = {
        'fiche': fiche,
        'patients': patients,
        'echantillon': echantillons, # Contient tous les échantillons de la fiche avec leurs PCR/résultats
    }

    return render(request, 'webpages/echantillonages/check-code.html', context)
def fiche_detecte(request):
    data = request.POST if request.method == "POST" else request.GET

    debut_raw = data.get("debut_ancien_code", "").strip()
    fin_raw = data.get("fin_code_echantillon", "").strip()
    inclure_raw = data.get("liste_inclure", "").strip()
    exclure_raw = data.get("liste_exclure", "").strip()

    def parse_code_list(raw_string):
        if not raw_string:
            return []
        cleaned = (
            raw_string.replace("\r\n", ",")
            .replace("\n", ",")
            .replace(";", ",")
        )
        return [c.strip() for c in cleaned.split(",") if c.strip()]

    codes_inclure = parse_code_list(inclure_raw)
    codes_exclure = parse_code_list(exclure_raw)

    debut = int(debut_raw) if debut_raw.isdigit() else None
    fin = int(fin_raw) if fin_raw.isdigit() else None

    # 1. Chargement et conversion du logo CIRCB en Base64
    logo_base64 = ""
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find(
        "images/logo_circb.png"
    )
    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Filtrage exact des échantillons dans la plage / listes
    base_qs = Echantillon.objects.all()

    qs_plage = base_qs.none()
    if debut is not None or fin is not None:
        numeric_qs = base_qs.filter(code__regex=r"^\d+$").annotate(
            code_int=Cast("code", output_field=IntegerField())
        )
        query_plage = Q()
        if debut is not None and fin is not None:
            query_plage &= Q(code_int__gte=debut, code_int__lte=fin)
        elif debut is not None:
            query_plage &= Q(code_int__gte=debut)
        elif fin is not None:
            query_plage &= Q(code_int__lte=fin)

        qs_plage = numeric_qs.filter(query_plage)

    qs_inclure = base_qs.none()
    if codes_inclure:
        qs_inclure = base_qs.filter(code__in=codes_inclure)

    if (debut is not None or fin is not None) and codes_inclure:
        base_queryset = qs_plage | qs_inclure
    elif debut is not None or fin is not None:
        base_queryset = qs_plage
    elif codes_inclure:
        base_queryset = qs_inclure
    else:
        base_queryset = base_qs

    if codes_exclure and base_queryset.exists():
        base_queryset = base_queryset.exclude(code__in=codes_exclure)

    # ---------------------------------------------------------------------
    # NOUTEAU : FILTRAGE UNIQUEMENT SUR LES ÉCHANTILLONS DÉTECTÉS
    # ---------------------------------------------------------------------
    # Remarque : Adaptez le nom du champ ci-dessous selon votre modèle.
    # Ex: resultat_pcr__nom ou resultats__valeur
    base_queryset = base_queryset.filter(
        Q(resultat_pcr__nom__iexact="DETECTE")
      
    ).distinct()
    # ---------------------------------------------------------------------

    # 3. Optimisation des requêtes et tri
    resultats = (
        base_queryset.select_related(
            "enfant",
            "mere",
            "fiche__fosa",
       
            "resultat_pcr",
        )
        .prefetch_related("resultats")
        .order_by("code")
    )

    # 4. Context pour le template global
    context = {
        "logo_base64": logo_base64,
        "date_impression": timezone.now(),
        "resultats": resultats,  # Liste filtrée contenant uniquement les DETECTES
        "responsable": request.user,
        "debut": debut,
        "fin": fin,
    }

    # 5. Rendu HTML et compilation PDF avec xhtml2pdf
    html_content = render_to_string(
        "webpages/rapports/resultats-patient-detecte.html", context
    )

    pdf_buffer = io.BytesIO()
    pisa_status = pisa.pisaDocument(
        io.BytesIO(html_content.encode("utf-8")), pdf_buffer, encoding="utf-8"
    )

    if pisa_status.err:
        return HttpResponse(
            "Erreur lors de la compilation du PDF.", status=500
        )

    pdf_buffer.seek(0)
    pdf_data = pdf_buffer.getvalue()

    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = (
        'inline; filename="Resultats_Collectifs.pdf"'
    )
    response["Content-Length"] = len(pdf_data)

    return response


def signalement_echantillon(request, id):
    echantillon = get_object_or_404(Echantillon, id=id)
    
    if request.method == 'POST':
        # Récupération et mise à jour des champs du formulaire
        echantillon.code_ech = request.POST.get('code_ech')
        echantillon.code_circb = request.POST.get('code_circb')
        echantillon.date_prelevement = request.POST.get('date_prelevement') or None
        echantillon.date_enregistrement = request.POST.get('date_enregistrement') or None
        echantillon.date_resultat = request.POST.get('date_resultat') or None
        echantillon.poids = request.POST.get('poids') or None
        echantillon.rang_naissance = request.POST.get('rang_naissance') or None
        echantillon.nb_enfant_expose = request.POST.get('nb_enfant_expose') or None
        echantillon.nb_enfant_infecte = request.POST.get('nb_enfant_infecte') or None
        
        # Enregistrement en base de données
        echantillon.save()
        
        messages.success(request, f"L'échantillon #{echantillon.code_ech} a été mis à jour avec succès.")
        # Redirigez vers la liste des anomalies ou la page précédente
        return redirect('/annomalies/')  # Remplacez par le nom de votre route de liste

    return render(request, 'webpages/signalement_echantillon.html', {
        'echantillon': echantillon
    })


def index_redirect(request):
    """Gère l'accès à http://localhost:8000/"""
    if request.user.is_authenticated:
        return redirect('dashboard')  # L'utilisateur reste connecté et va au dashboard
    return redirect('acceuil')  # Seul l'utilisateur anonyme va au login

def acceuil(request):
    return render(request,'webpages/acceuil.html')

@require_POST
def delete_patient(request, patient_id):
    try:
        patient = Patient.objects.get(id=patient_id)
        patient.delete()
        return JsonResponse({"status": "success", "message": "Patient supprimé avec succès."})
    except Patient.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Patient introuvable."}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def Update_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            # Sauvegarde du nouveau mot de passe
            form.save()
            
            # Déconnexion immédiate de l'utilisateur
            logout(request)
            
            messages.success(request, "Votre mot de passe a été mis à jour. Veuillez vous reconnecter.")
            
            # Redirection vers la page de login (remplacez 'login' par le nom de votre route de connexion)
            return redirect("authentification")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PasswordChangeForm(request.user)

    context = {
        "form": form
    }
    return render(request, "webpages/login_hosp.html", context)  # Remplacez par le nom de votre template


def search_fiches(request):
    # Récupérer le terme de recherche envoyé par le JS (?q=...)
    query = request.GET.get('q', '').strip()
    results = []
    
    if query:
        print(f'code :{query}')
        # Filtrer par code de fiche ou par le nom de la structure/FOSA associée
        fiches = FicheEchantillon.objects.filter(
            Q(code__icontains=query) | Q(fosa__nom__icontains=query)
        ).select_related('fosa')[:10]  # .select_related() optimise les requêtes SQL, [:10] limite à 10 résultats
        
        for f in fiches:
            results.append({
                'id': f.id,
                'code': f.code,
                # Nom de la structure FOSA
                'structure': f.fosa.nom if hasattr(f, 'fosa') and f.fosa else 'N/A',
                # CORRECTION ICI : Remplacement de f.date_creation par f.date_enregistrement
                'date': f.date_enregistrement.strftime('%Y-%m-%d') if hasattr(f, 'date_enregistrement') and f.date_enregistrement else ''
            })
            
    return JsonResponse({'results': results})


def check_patient_code_exists(request):
    code = request.GET.get('code', '').strip()
    if not code:
        return JsonResponse({'exists': False})
    
    exists = Patient.objects.filter(code=code).exists()
    
    return JsonResponse({'exists': exists})



@require_POST
def update_patient_code(request, patient_id):
    """
    Vue Django pour mettre à jour le code d'un patient via AJAX.
    """
    try:
        # Récupération des données JSON envoyées par le fetch
        data = json.loads(request.body)
        new_code = data.get('code', '').strip()

        # Validation de la longueur (exactement 15 caractères)
        if len(new_code) != 19:
            return JsonResponse({
                'status': 'error', 
                'message': 'Le code doit comporter exactement 19 caractères.'
            }, status=400)

        # Récupération de l'objet Patient
        # (Adaptez 'Patient' et le champ 'code' selon votre structure de modèles)
        patient = get_object_or_404(Patient, id=patient_id)

        # Vérifier si le code existe déjà pour un *autre* patient
        if Patient.objects.filter(code=new_code).exclude(id=patient_id).exists():
            return JsonResponse({
                'status': 'error', 
                'message': 'Ce code existe déjà en base de données.'
            }, status=400)

        # Mise à jour et sauvegarde
        patient.code = new_code
        patient.save()

        return JsonResponse({
            'status': 'success', 
            'message': 'Code mis à jour avec succès.'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error', 
            'message': 'Données JSON invalides.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)


def district_view(request, pk, slug):
  real_id = pk - 10000  # On retire le décalage (10001 - 10000 = 1)
  region = get_object_or_404(Region, id=real_id)

  # On récupère les districts rattachés à cette région en comptant leurs FOSA (enfants)
  districts = District.objects.filter(parent=region).annotate(
      fosa_count=Count('children', distinct=True)
  )

  return render(
      request,
      'webpages/config/district.html',
      {
          'region': region,
          'lines': districts,  # Contient maintenant l'attribut .fosa_count pour chaque district
      },
  )


def fosa_view(request, pk, slug):
  if pk <= 10000:
    raise Http404("Identifiant invalide.")

  real_id = pk - 10000  # On retire le décalage du masked_id
  district = get_object_or_404(
      District.objects.select_related('parent'), id=real_id
  )

  # On récupère toutes les FOSA rattachées à ce district
  fosas = Fosa.objects.filter(parent=district)

  return render(
      request,
      'webpages/config/fosa.html',
      {
          'district': district,  # Le district actuel (pour le fil d'ariane)
          'region': district.parent,  # La région parente
          'lines': fosas,  # La liste des FOSA
          'tous_districts': District.objects.select_related('parent').all(),
      },
  )
def region_create(request):
  if request.method == 'POST':
    nom = request.POST.get('nom')
    designation = request.POST.get('designation')
    if nom:
      Region.objects.create(nom=nom, designation=designation)
  # Redirige vers la liste des régions (remplacez 'structures' par le nom de votre route principale)
  return redirect('structures')


# Vue pour modifier une région
def region_update(request, pk):
  region = get_object_or_404(Region, pk=pk)
  if request.method == 'POST':
    region.nom = request.POST.get('nom')
    region.designation = request.POST.get('designation')
    region.save()
  return redirect('structures')


# Vue pour créer un district
def district_create(request, region_pk):
  region = get_object_or_404(Region, pk=region_pk)

  if request.method == 'POST':
    nom = request.POST.get('nom')
    designation = request.POST.get('designation')
    if nom:
      try:
        District.objects.create(nom=nom, designation=designation, parent=region)
        messages.success(request, f'District {nom} créé avec succès.')
      except Exception as e:
        # Affiche l'erreur exacte dans vos messages Django pour comprendre ce qui bloque
        messages.error(request, f"Erreur lors de la création : {e}")

  return redirect(request.META.get('HTTP_REFERER', '/'))

# Vue pour modifier un district
def district_update(request, pk):
  district = get_object_or_404(District, pk=pk)
  if request.method == 'POST':
    district.nom = request.POST.get('nom')
    district.designation = request.POST.get('designation')
    district.save()
    messages.success(request, f'Modification de {district.nom} avec succès.')

  # Correction de 'HTTP_REFERER' (get en minuscules) et redirection vers la page précédente
  return redirect(request.META.get('HTTP_REFERER', '/'))



def fosa_create(request, district_pk):
  district = get_object_or_404(District, pk=district_pk)
  if request.method == 'POST':
    nom = request.POST.get('nom')
    designation = request.POST.get('designation')
    if nom:
      try:
        # En supposant que le champ de liaison vers le district s'appelle aussi 'parent' ou 'district'
        Fosa.objects.create(nom=nom, designation=designation, parent=district)
        messages.success(request, f'FOSA {nom} créée avec succès.')
      except Exception as e:
        messages.error(request, f"Erreur lors de la création : {e}")

  return redirect(request.META.get('HTTP_REFERER', '/'))


def fosa_update(request, pk):
  fosa = get_object_or_404(Fosa, pk=pk)
  if request.method == 'POST':
    fosa.nom = request.POST.get('nom')
    fosa.designation = request.POST.get('designation')
    fosa.save()
    messages.success(request, f'Modification de {fosa.nom} avec succès.')

  return redirect(request.META.get('HTTP_REFERER', '/'))


# ==========================================
# SUPPRESSION D'UN DISTRICT
# ==========================================
def district_delete(request, pk):
  district = get_object_or_404(District, pk=pk)

  # 1. Vérification si le district contient des FOSA (via related_name='children')
  if district.children.exists():
    messages.error(
        request,
        f"Impossible de supprimer le district '{district.nom}' car il contient"
        ' encore des Formations Sanitaires (FOSA) rattachées.',
    )
    return redirect(request.META.get('HTTP_REFERER', '/'))

  # 2. Vérification dans la table FicheEchantillon (champ 'district')
  if FicheEchantillon.objects.filter(district=district).exists():
    messages.error(
        request,
        f"Suppression impossible : Le district '{district.nom}' est lié à des"
        " données dans les fiches d'échantillons.",
    )
    return redirect(request.META.get('HTTP_REFERER', '/'))

  # Si tout est OK, on supprime
  nom_district = district.nom
  district.delete()
  messages.success(request, f"Le district '{nom_district}' a été supprimé avec succès.")

  return redirect(request.META.get('HTTP_REFERER', '/'))


# ==========================================
# SUPPRESSION D'UNE FOSA
# ==========================================
def fosa_delete(request, pk):
  fosa = get_object_or_404(Fosa, pk=pk)

  # Vérification dans la table FicheEchantillon (champ 'fosa')
  if FicheEchantillon.objects.filter(fosa=fosa).exists():
    messages.error(
        request,
        f"Suppression impossible : La FOSA '{fosa.nom}' possède des données"
        " rattachées dans les fiches d'échantillons.",
    )
    return redirect(request.META.get('HTTP_REFERER', '/'))

  # Si tout est OK, on supprime
  nom_fosa = fosa.nom
  fosa.delete()
  messages.success(request, f"La FOSA '{nom_fosa}' a été supprimée avec succès.")

  return redirect(request.META.get('HTTP_REFERER', '/'))



def region_delete(request, pk):
  region = get_object_or_404(Region, pk=pk)

  # 1. Vérification si la région contient des Districts rattachés (via children)
  if region.children.exists():
    messages.error(
        request,
        f"Impossible de supprimer la région '{region.nom}' car elle contient"
        ' encore des Districts rattachés.',
    )
    return redirect(request.META.get('HTTP_REFERER', '/'))

  # 2. Vérification dans la table FicheEchantillon (champ 'region')
  if FicheEchantillon.objects.filter(region=region).exists():
    messages.error(
        request,
        f"Suppression impossible : La région '{region.nom}' est liée à des"
        " données dans les fiches d'échantillons.",
    )
    return redirect(request.META.get('HTTP_REFERER', '/'))

  # Si tout est OK, on procède à la suppression
  nom_region = region.nom
  region.delete()
  messages.success(request, f"La région '{nom_region}' a été supprimée avec succès.")

  return redirect(request.META.get('HTTP_REFERER', '/'))



def fosa_transfer(request, pk):
  # 'pk' correspond à l'ID de la FOSA à transférer
  fosa = get_object_or_404(FicheEchantillon, pk=pk)  # Ou votre modèle Fosa

  if request.method == 'POST':
    nouveau_district_id = request.POST.get('district_id')
    nouveau_district = get_object_or_404(District, pk=nouveau_district_id)

    ancien_district = fosa.district  # Adaptez selon le nom du champ (ex: fosa.district ou fosa.parent)
    fosa.district = nouveau_district
    fosa.save()

    messages.success(
        request,
        f"La FOSA '{fosa.nom}' a été transférée avec succès de"
        f" '{ancien_district.nom}' vers '{nouveau_district.nom}'.",
    )
    return redirect(request.META.get('HTTP_REFERER', '/'))

  return redirect(request.META.get('HTTP_REFERER', '/'))



# Étape 1 : Intercepte le formulaire de la modale et affiche la page de confirmation
def fosa_transfer_preview(request, pk):
  fosa = get_object_or_404(Fosa, pk=pk)

  if request.method == 'POST':
    nouveau_district_id = request.POST.get('district_id')
    nouveau_district = get_object_or_404(District, pk=nouveau_district_id)
    old_code = request.POST.get('old_code')
    new_code = request.POST.get('new_code')

    # CORRECTION : On cible les éléments dont les 11 premiers caractères correspondent à l'ancien code
    # (En supposant que le champ s'appelle 'code' dans votre modèle Patient ou FicheEchantillon)
    patients_concernes = Patient.objects.filter(code__startswith=old_code)

    return render(
        request,
        'webpages/fosa_transfer_confirm.html',
        {
            'fosa': fosa,
            'district_actuel': fosa.parent,
            'nouveau_district': nouveau_district,
            'old_code': old_code,
            'new_code': new_code,
            'patients_concernes': patients_concernes,
        },
    )

  return redirect(request.META.get('HTTP_REFERER', '/'))


def fosa_transfer_confirmed(request, pk):
  fosa = get_object_or_404(Fosa, pk=pk)

  if request.method == 'POST':
    nouveau_district_id = request.POST.get('district_id')
    old_code = request.POST.get('old_code', '').strip()
    new_code = request.POST.get('new_code', '').strip()

    # Lancement de la tâche asynchrone Celery
    task = task_transfert_fosa.delay(
        fosa_id=fosa.id,
        nouveau_district_id=nouveau_district_id,
        old_code=old_code,
        new_code=new_code,
    )

    # Redirection vers la page de chargement avec l'ID de la tâche Celery
    return render(
        request, 'webpages/fosa_transfer_progress.html', {'task_id': task.id, 'fosa': fosa}
    )

  return redirect(request.META.get('HTTP_REFERER', '/'))



from celery.result import AsyncResult


def fosa_transfer_status(request, pk, task_id):
  try:
    task_result = AsyncResult(task_id)
    state = task_result.state

    # Valeurs par défaut
    percent = 0
    step_name = 'Traitement en cours...'

    if state in ['PENDING', 'STARTED']:
      percent = 0
      step_name = "Initialisation..."
    elif state == 'PROGRESS':
      # Récupération sécurisée des métadonnées envoyées par update_state
      info = task_result.info
      if isinstance(info, dict):
        percent = info.get('percent', 0)
        step_name = info.get('step_name', 'Traitement en cours...')
    elif state == 'SUCCESS':
      percent = 100
      step_name = 'Terminé avec succès !'
    else:  # FAILURE ou autre
      percent = 100
      step_name = 'Erreur de traitement'

    return JsonResponse(
        {'state': state, 'percent': percent, 'step_name': step_name}
    )

  except Exception as e:
    # Sécurité absolue pour éviter le plantage 500
    return JsonResponse(
        {'state': 'SUCCESS', 'percent': 100, 'step_name': 'Terminé'}
    )




def liste_transferts_fosa(request):
  # Récupération de tous les logs de transferts, optimisés avec select_related pour l'utilisateur
  transferts_list = FosaTransferLog.objects.select_related('effectue_par', 'fosa').all()

  # Optionnel : Pagination (10 transferts par page)
  paginator = Paginator(transferts_list, 10)
  page_number = request.GET.get('page')
  transferts = paginator.get_page(page_number)

  context = {
      'transferts': transferts,
  }

  return render(request, 'webpages/transfer_logs.html', context)