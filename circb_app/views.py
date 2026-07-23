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
from django.db import IntegrityError
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.utils.crypto import get_random_string
from django.db.models import Q
# 1. On garde l'import de Django sous un autre nom ou on importe ton fichier models local
from .models import Structure_Hierachy, Structure 
# Create your views here.
def connexion_view(request):
    # Django ira chercher ce fichier dans vos dossiers de templates configurés
    return render(request, 'webpages/login_hosp.html')

@login_required(login_url='/')
def dashboard(request):
    return render(request, 'webpages/dashbord_hosp.html')
@login_required(login_url='/')
def personnel(request):
    context ={
        'user':User.objects.all(),
        'role':Role.objects.all(),
        'personnels': Personnel.objects.all(),
    }
    return render(request, 'webpages/personnel.html',context)


def authentification(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"--- TENTATIVE DE CONNEXION --- Username soumis: '{username}' | Password soumis: '{password}'")
        
        # Sécurité/Nettoyage : On retire les espaces superflus si l'utilisateur en a mis par erreur
        if username:
            username = username.strip()
            
        # Authentification native de Django
        user = authenticate(request, username=username, password=password)
        print(f"--- RÉSULTAT AUTHENTICATE --- Objet User trouvé: {user}")
        
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"Connexion réussie. Bienvenue, {user.username} !")
                return HttpResponse(status=200)  
            else:
                return HttpResponseBadRequest("Ce compte a été désactivé par l'administrateur.")
        else:
            return HttpResponseBadRequest("Nom d'utilisateur ou mot de passe incorrect.")
            
    return render(request, 'webpages/login_hosp.html')


def logout_view(request):
   
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect('/')  

@login_required(login_url='/')
def dossiers_patients(request):
    context ={
        'patients':Patient.objects.all()
    }
    return render(request, 'webpages/patients/dossiers.html', context)

@login_required(login_url='/')
def details_patient(request, slug):
    patient = get_object_or_404(Patient, code=slug)
    context ={
        'patient':patient,
        'echantillon':Echantillon.objects.filter(enfant=patient).order_by('-id')
    }
    return render(request, 'webpages/patients/details-patient.html', context)

@login_required(login_url='/')
def configurations(request):
    context = {
        'roles': Role.objects.all().order_by('id'),
    }
    return render(request, 'webpages/config/configurations.html', context)
@login_required(login_url='/')
def fiches_echantillons(request):
    dernier_numero= FicheEchantillon.objects.order_by('-numero_ordre').first()
    prochain_numero= (dernier_numero.numero_ordre + 1) if dernier_numero else 1
    context={
        'regions':Structure.objects.filter(parent__isnull=True).order_by('nom'),
        'transporteurs':Transporteur.objects.all().order_by('nom'),
        'moyens_transport':MoyenTransport.objects.all().order_by('nom'),
        'fiches':FicheEchantillon.objects.order_by('-id'),
        'dernier_numero':dernier_numero,
        'prochain_numero': prochain_numero
        
    }
    return render(request, 'webpages/echantillonages/fiche_echantillons.html', context)
@login_required(login_url='/')
def echantillons(request, id):
    context={
        'fiches_echantillon':FicheEchantillon.objects.get(id=id),
        'tests':Test.objects.all().order_by('nom'),
        'raisons_prelevement':RaisonPrelevement.objects.all().order_by('nom'),
        'modes_allaitement':ModeAllaitement.objects.all().order_by('nom'),
        'resultats_pcr':ResultatPcr.objects.all().order_by('nom'),
        'regions':Structure.objects.filter(parent__isnull=True).order_by('nom'),
        'portes_entree':PorteEntree.objects.all().order_by('nom'),
        'protocole_ptme':ProtocolePTME.objects.all().order_by('nom'),
        'profilaxie_arv':ProfilaxieArv.objects.all(),
        'mode_accouchement': ModeAccouchement.objects.all()
    }
    return render(request, 'webpages/echantillonages/echantillons.html', context)
@login_required(login_url='/')
def echantillonages(request):
    fiches = FicheEchantillon.objects.all().order_by('id')
    
   

    context = {
        'fiches': fiches,
    }
    return render(request, 'webpages/echantillonages/echantillonages.html', context)

@login_required(login_url='/')


def structures(request):
    context = {}

    # 2. Utilise directement les classes importées sans le préfixe "models."
    hierachie = Structure_Hierachy.objects.all().order_by('rang')

    # 3. Récupération des racines
    lines = Structure.objects.filter(
        parent__isnull=True
    ).prefetch_related('children', 'hierachy')

    # 4. Liste complète pour le select du Modal
    context['all_structures'] = Structure.objects.all().select_related('hierachy').order_by('hierachy__rang', 'nom')

    context['hierachie'] = hierachie
    context['lines'] = lines
    
    return render(request, 'webpages/config/structure.html', context)
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
    districts = Structure.objects.filter(parent_id=region_id).values('id', 'nom')
    # On renvoie la clé 'results' comme attendu par votre JS
    return JsonResponse({'results': list(districts)})

def search_fosa(request, district_id):
    # On filtre les FOSAs qui ont le district comme parent
    fosas = Structure.objects.filter(parent_id=district_id).values('id', 'nom').order_by('nom')
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
def enregistrer_fiche_echantillon(request):
    if request.method == "POST":
        # 1. Récupération des données
        data = request.POST
        
        region_id = data.get('region')
        district_id = data.get('district')
        fosa_id = data.get('fosa')
        transporteur_id = data.get('transporteur') or None
        moyen_id = data.get('moyen_transport') or None
        
        # On utilise directement l'ID de l'utilisateur connecté pour éviter les erreurs
        receptioniste = request.user 
        
        code = data.get('code')
        date_reception = data.get('date_reception')
        date_expedition = data.get('date_expedition')
        date_enregistrement = data.get('date_enregistrement')
        nombre_echantillon = data.get('nombre_echantillon')
        observation = data.get('observation')
        numero_ordre = data.get('numero_ordre')

        # 3. Validation simplifiée
        required_fields = [region_id, district_id, fosa_id, date_reception, date_expedition, nombre_echantillon, date_enregistrement]
        if not all(required_fields):
            return JsonResponse({'success': False, 'errors': 'Champs obligatoires manquants.'}, status=400)

        try:
            # 4. Création de la fiche
            # Note: On passe l'objet User (receptioniste) directement si c'est une ForeignKey
            fiche = FicheEchantillon.objects.create(
                code=code,
                region_id=region_id,
                district_id=district_id,
                fosa_id=fosa_id,
                transporteur_id=transporteur_id,
                moyen_transport_id=moyen_id,
                receptioniste=receptioniste, 
                date_reception=date_reception,
                date_expedition=date_expedition,
                date_enregistrement=date_enregistrement,
                nombre_echantillon=nombre_echantillon,
                observation=observation,
                numero_ordre=numero_ordre
            )

            return redirect('verification-code', code=fiche.code)

        except IntegrityError as e:
            messages.error(request, f"Erreur BDD: {str(e)}")
        except Exception as e:
          
            messages.error(request, f"Erreur BDD: {str(e)}")

    return redirect(request.META.get('HTTP_REFERER','/'))

def details_fiche(request, slug):
    fiche = FicheEchantillon.objects.get(code=slug)
    context ={
        'fiche':fiche,
        'echantillons':fiche.echantillons.all()
    }
    return render(request, 'webpages/echantillonages/details-fiche-echantillonage.html', context)

def detail_fiche(request, code):
    pass
    
def ajouter_echantillon(request):
    if request.method == 'POST':
        # Détection de la nature de la requête AJAX
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
            request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        )
        
        if is_ajax:
            fiche_id = request.POST.get('fiche_echantillon')
            enfant_id = request.POST.get('enfant_id')
            mere_id = request.POST.get('enfant_mere_id')

            try:
                # Récupération de la fiche (Obligatoire)
                fiche = FicheEchantillon.objects.filter(id=fiche_id).first() if fiche_id else None
                if not fiche:
                    return JsonResponse({'success': False, 'error': "La fiche d'échantillon associée est introuvable ou manquante."}, status=400)

                # --- Fonctions Helpers de Nettoyage de Données ---
                # Interprète "oui" comme True et tout le reste (dont "non") comme False
                def p_bool(val):
                    if val is None: return False
                    return str(val).strip().lower() == 'oui'

                def p_int(val):
                    return int(val) if val and str(val).isdigit() else None

                def p_float(val):
                    if not val: return None
                    try: return float(str(val).replace(',', '.'))
                    except ValueError: return None

                def p_date(val):
                    if not val: return None
                    try: return datetime.strptime(val, '%Y-%m-%d').date()
                    except ValueError: return None

                # --- Création de l'enregistrement dans une transaction sécurisée ---
                with transaction.atomic():
                    echantillon = Echantillon.objects.create(
                        fiche=fiche,
                        
                        # INFORMATIONS SUR ENFANT
                        enfant_id=p_int(enfant_id),
                        rang_naissance=p_int(request.POST.get('rang_naissance')),
                        poids=p_float(request.POST.get('poids')),
                        profilaxie_arv_id=p_int(request.POST.get('profilaxie_arv')),
                        
                        # INFORMATIONS SUR MERE
                        mere_id=p_int(mere_id),
                        protocole_ptme_id=p_int(request.POST.get('protocole_ptme')),
                        date_rdv=p_date(request.POST.get('date_prochain_rdv')),
                        date_initiation_ptme=p_date(request.POST.get('date_initiation_ptme')),
                        date_diagnostic_vih=p_date(request.POST.get('date_diagnostic_vih')),
                        numero_grossesse=p_int(request.POST.get('numero_grossesse')),
                        nb_enfant_expose=p_int(request.POST.get('nb_enfant_expose')),
                        nb_enfant_infecte=p_int(request.POST.get('nb_enfant_infecte')),
                        mode_accouchement_id=p_int(request.POST.get('mode_accouchement')),
                        date_diagnostic_lav=p_date(request.POST.get('date_diagnostic_lav')),
                        
                        # SUIVI VIROLOGIQUE (Analyse rigoureuse du Oui/Non)
                        present_symptome=p_bool(request.POST.get('enfant_symptomatique')),
                        present_allaitement=p_bool(request.POST.get('enfant_allaite')),
                        mode_allaitement_id=p_int(request.POST.get('mode_allaitement')),
                        present_sevrage=p_bool(request.POST.get('statut_sevrage')),
                        date_sevrage=p_date(request.POST.get('date_sevrage')),
                        present_cotrimoxazole=p_bool(request.POST.get('sous_cotrim')),
                        date_cotrimoxazole=p_date(request.POST.get('date_initiation_cotrim')),
                        present_tarv=p_bool(request.POST.get('sous_tarv')),
                        date_tarv=p_date(request.POST.get('date_initiation_tarv')),
                        
                        # Gestion des PCRs et raison
                        pcr_1=p_bool(request.POST.get('date_pcr1')), 
                        pcr_2=p_bool(request.POST.get('date_pcr2')),
                        autre_pcr=p_bool(request.POST.get('autre_pcr')),
                        resultat_pcr_id=p_int(request.POST.get('resultat_pcr')),
                        raison_prelevement_id=p_int(request.POST.get('raisons_prelevement')),
                        
                        # INFOS PRÉLÈVEMENT
                        date_prelevement=p_date(request.POST.get('date_prelevement')),
                        duplicate_prelevement=p_bool(request.POST.get('duplicate_prelevement')),
                        nom_preleveur=request.POST.get('nom_preleveur', '').strip(),
                        prenom_preleveur=request.POST.get('prenom_preleveur', '').strip(),
                        contact_preleveur=p_int(request.POST.get('contact_preleveur')),
                        observation=request.POST.get('observation', '').strip(),
                    )
                
                return JsonResponse({
                    'success': True, 
                    'message': "L'échantillon sanitaire a été enregistré avec succès en base de données."
                })

            except Exception as e:
                return JsonResponse({'success': False, 'error': f"Erreur base de données : {str(e)}"}, status=500)
        
        return JsonResponse({'success': False, 'error': "Méthode ou protocole de requête invalide."}, status=400)

    # Gestion classique du flux GET initial
    return render(request, 'webpages/echantillonages/echantillons.html', {})

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
        'personnels': Personnel.objects.all(),
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

from django.http import JsonResponse

def verifier_patient(request):
    """Vérifie l'existence d'un patient par son code unique complet"""
    code_recherche = request.GET.get('code', '').strip()
    
    if not code_recherche:
        return JsonResponse({'existe': False, 'erreur': 'Code manquant'}, status=400)
    
    # Recherche du patient dans la base de données
    patient = Patient.objects.filter(code=code_recherche).first()
    
    if patient:
        # Construction sécurisée du dictionnaire de la mère si elle existe
        mere_data = None
        if patient.mere:
            mere_data = {
                'id': patient.mere.id,
                'nom': patient.mere.nom,
                'prenom': patient.mere.prenom if hasattr(patient.mere, 'prenom') else '',
                'contact': patient.mere.contact.id if patient.mere.contact else None,
                'age': patient.mere.age if hasattr(patient.mere, 'age') else None,
                'date_naissance': patient.mere.date_naissance.strftime('%Y-%m-%d') if patient.mere.date_naissance else None,
                
            }

        return JsonResponse({
            'existe': True,
            'patient': {
                'id': patient.id,
                'nom': patient.nom,
                'prenom': patient.prenom,
                'sexe': patient.sexe,
                'porte_entree': patient.porte_entree.id if patient.porte_entree else None,
                'date_naissance': patient.date_naissance.strftime('%Y-%m-%d') if patient.date_naissance else None,
                'mere': mere_data,  # Renvoie un dictionnaire structuré ou None
            }
        })
    else:
        return JsonResponse({'existe': False})

from django.shortcuts import render
from django.http import JsonResponse
from .models import Structure, PorteEntree, Patient, Mere  # Assure-toi d'importer ton modèle Mere
from datetime import datetime
from django.db import transaction
import sys
def creer_patient(request):
    if request.method == 'POST':
        # Détection robuste de la requête AJAX
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
            request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        )
        
        if is_ajax:
            try:
                with transaction.atomic():
                    # 1. Extraction des données de l'enfant depuis le Modal
                    nom_enfant = request.POST.get('nom', '').strip()
                    prenom_enfant = request.POST.get('prenom', '').strip()
                    sexe_enfant = request.POST.get('sexe', '').strip()
                    dob_enfant_str = request.POST.get('date_naissance', '').strip()
                    poids_enfant_str = request.POST.get('poids', '').strip()
                    code_enfant = request.POST.get('code', '').strip()  # Code combiné (ex: LT-DEIDO-...)
                    
                    fosa_id = request.POST.get('fosa', '').strip()
                    porte_entree_id = request.POST.get('porte_entree', '').strip()
                    personnel_id = request.POST.get('contact', '').strip()

                    # 2. Extraction des données de la mère depuis le Modal
                    mere_nom = request.POST.get('mere_nom', '').strip()
                    mere_prenom = request.POST.get('mere_prenom', '').strip()
                    mere_age_str = request.POST.get('mere_age', '').strip()
                    mere_dob_str = request.POST.get('mere_date_naissance', '').strip()

                    # Validation minimale obligatoire
                    if not nom_enfant or not sexe_enfant or not mere_nom:
                        return JsonResponse({
                            'success': False, 
                            'error': 'Le nom, le sexe de l’enfant et le nom de la mère sont obligatoires.'
                        }, status=400)

                    # 3. Traitement, conversion et nettoyage des types
                    date_naissance_enfant = datetime.strptime(dob_enfant_str, '%Y-%m-%d').date() if dob_enfant_str else None
                    mere_dob = datetime.strptime(mere_dob_str, '%Y-%m-%d').date() if mere_dob_str else None
                    
                    poids_enfant = None
                    if poids_enfant_str:
                        poids_enfant = float(poids_enfant_str.replace(',', '.'))
                    
                    mere_age = int(mere_age_str) if mere_age_str.isdigit() else None

                    # Récupération sécurisée des instances de clés étrangères (ForeignKeys)
                    personnel_instance = Personnel.objects.filter(id=personnel_id).first() if personnel_id.isdigit() else None
                    fosa_instance = Structure.objects.filter(id=fosa_id).first() if fosa_id.isdigit() else None
                    porte_instance = PorteEntree.objects.filter(id=porte_entree_id).first() if porte_entree_id.isdigit() else None

                    # 4. Enregistrement de la Mère
                    nouvelle_mere = Mere.objects.create(
                        nom=mere_nom,
                        prenom=mere_prenom,
                        age=mere_age,
                        date_naissance=mere_dob,
                       
                        contact=personnel_instance  # Utilisation sécurisée de l'instance réseau récupérée
                    )

                    # 5. Enregistrement de l'Enfant (Patient)
                    nouveau_patient = Patient.objects.create(
                        code=code_enfant,
                        nom=nom_enfant,
                        prenom=prenom_enfant,
                        sexe=sexe_enfant,
                        date_naissance=date_naissance_enfant,
                        poids=poids_enfant,
                       
                        fosa=fosa_instance,
                        porte_entree=porte_instance,
                        mere=nouvelle_mere
                    )

                    # 6. Réponse JSON renvoyée pour alimenter directement ta page principale
                    return JsonResponse({
                        'success': True,
                        'patient': {
                            'id': nouveau_patient.id,
                            'nom': nouveau_patient.nom,
                            'prenom': nouveau_patient.prenom,
                            'sexe': nouveau_patient.sexe,
                            'date_naissance': nouveau_patient.date_naissance.strftime('%Y-%m-%d') if nouveau_patient.date_naissance else '',
                            'poids': float(nouveau_patient.poids) if nouveau_patient.poids else '',
                            'porte_entree': nouveau_patient.porte_entree.id if nouveau_patient.porte_entree else '',
                            'mere': {
                                'id': nouvelle_mere.id,
                                'nom': nouvelle_mere.nom,
                                'prenom': nouvelle_mere.prenom,
                                'age': nouvelle_mere.age,
                                'date_naissance': nouvelle_mere.date_naissance.strftime('%Y-%m-%d') if nouvelle_mere.date_naissance else ''
                            }
                        }
                    })

            except Exception as e:
                print(f"!!! ERREUR CRITIQUE DJANGO : {str(e)}", file=sys.stderr)
                return JsonResponse({'success': False, 'error': f'Erreur BDD : {str(e)}'}, status=500)
        
        return JsonResponse({'success': False, 'error': 'Requête AJAX invalide.'}, status=400)

    # ==========================================
    # CHARGEMENT INITIAL DE LA PAGE (Méthode GET)
    # ==========================================
    regions = Structure.objects.filter(parent__isnull=True).order_by('nom')
    portes_entree = PorteEntree.objects.all().order_by('nom')
    personnels = Personnel.objects.all().order_by('nom')

    context = {
        'regions': regions,
        'portes_entree': portes_entree,
        'personnels': personnels
    }

    return render(request, 'webpages/echantillonages/echantillons.html', context)

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

def delete_role(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    role.delete()
    messages.success(request, f"Le rôle '{role.nom}' a été supprimé avec succès.")
    return redirect('/configurations/')  # Remplacez par le nom de votre URL de redirection pour la liste des rôles

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


def resultats(request):
    context ={
        'resultats':Resultat.objects.all()
    }
    return render(request, 'webpages/resultats/list_resultat.html',context)

import io
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Resultat

def imprimer_resultat_pdf(request, resultat_id):
    resultat = get_object_or_404(Resultat, id=resultat_id)
    
    # Préparation d'un contexte propre et simplifié
    context = {
        'id_run': resultat.id,
        'echantillon_code': resultat.echantillon.code_barre if hasattr(resultat.echantillon, 'code_barre') else resultat.echantillon,
        'test_nom': resultat.test.nom if resultat.test else "Non spécifié",
        'verdict': (resultat.resultat_pcr.nom if resultat.resultat_pcr else "En attente").upper(),
        'date_prelevement': resultat.date_prelevement, # Le filtre Django gérera le format dans le template
        'commentaire': resultat.commentaire or "Aucun commentaire particulier mentionné.",
    }

    # 1. Rendu du template HTML sous forme de chaîne de caractères
    html_content = render_to_string('webpages/resultats/resultat_pdf.html', context)

    # 2. Préparation de la réponse HTTP binaire
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Resultat_{resultat.id}.pdf"'
    
    # 3. Génération sécurisée du PDF
    pisa_status = pisa.pisaDocument(
        io.BytesIO(html_content.encode("utf-8")),
        response,
        encoding='utf-8'
    )
    
    if pisa_status.err:
        return HttpResponse("Erreur lors de la compilation du PDF.", status=500)
        
    return response


def bordeaux_sortie(request):
    return render(request, 'webpages/borderaux.html')



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

def fiches(request):
    dernier_numero= FicheEchantillon.objects.order_by('-numero_ordre').first()
    prochain_numero= (dernier_numero.numero_ordre + 1) if dernier_numero else 1
    context={
        'regions':Structure.objects.filter(parent__isnull=True).order_by('nom'),
        'transporteurs':Transporteur.objects.all().order_by('nom'),
        'moyens_transport':MoyenTransport.objects.all().order_by('nom'),
        'fiches':FicheEchantillon.objects.all(),
        'dernier_numero':dernier_numero,
        'prochain_numero': prochain_numero
        
    }
    return render(request,'webpages/echantillonages/fiches.html', context)




def verification_code(request, code):
    fiche = FicheEchantillon.objects.get(code=code)
    # Create the range here in Python
    sample_range = range(fiche.nombre_echantillon)
    
    context = {
        'fiche': fiche,
        'porte_entree': PorteEntree.objects.all(),
        'sample_range': sample_range # Pass this to the template
    }
    return render(request, 'webpages/echantillonages/verification-code.html', context)



def rechercher_patient(request):
    code = request.GET.get('code', '').strip().upper()
    patient = Patient.objects.filter(code=code).first()
    
    if patient:
        # Construction sécurisée du dictionnaire de la mère
        mere_data = None
        if patient.mere:
            mere_data = {
                'id': patient.mere.id,
                'nom': patient.mere.nom,
                'prenom': patient.mere.prenom if hasattr(patient.mere, 'prenom') else '',
                'contact': patient.mere.contact.id if patient.mere.contact else None,
                'age': patient.mere.age if hasattr(patient.mere, 'age') else None,
                'date_naissance': patient.mere.date_naissance.strftime('%Y-%m-%d') if patient.mere.date_naissance else None,
            }

        return JsonResponse({
            'exists': True, # Unifié en 'exists'
            'patient': {
                'id': patient.id,
                'code':patient.code,
                'nom': patient.nom,
                'prenom': patient.prenom,
                'sexe': patient.sexe,
                'porte_entree': patient.porte_entree.id if patient.porte_entree else None,
                'date_naissance': patient.date_naissance.strftime('%Y-%m-%d') if patient.date_naissance else None,
                'mere': mere_data,
            }
        })
    else:
        # Correction ici : utilisez 'exists' aussi
        return JsonResponse({'exists': False})



def delete_role(request, id):
    role = Role.objects.get(id=int(id))
    role.delete()
    messages.success(request, 'suppression reussie')
    return redirect(request.META.get('HTTP_REFERER','/'))



def save_personnel(request):
    if request.method == "POST":
        try:
            nom = request.POST.get('last_name')
            prenom = request.POST.get('first_name')
            email = request.POST.get('email')
            service = request.POST.get('service')
            role_id = request.POST.get('role')

            if not all([nom, prenom, email, service, role_id]):
                return JsonResponse({'success': False, 'message': 'Tous les champs sont requis.'}, status=400)

            # Utilisation de transaction.atomic pour éviter les données orphelines
            with transaction.atomic():
                # 1. Création de l'utilisateur
                # On génère un mot de passe aléatoire de 12 caractères
                password = get_random_string(length=12)
                user = User.objects.create_user(
                    username=email, # L'email sert de login
                    email=email,
                    password=password,
                    first_name=prenom,
                    last_name=nom
                )

                # 2. Création de l'instance Personnel liée à cet utilisateur
                personnel = Personnel.objects.create(
                    nom=nom,
                    prenom=prenom,
                    mail=email,
                    service=service,
                    bd_user=user
                )

                # 3. Ajout du rôle
                role = Role.objects.get(id=role_id)
                personnel.roles.add(role)

            # Vous pourriez envoyer ce mot de passe par email ici
            return JsonResponse({
                'success': True, 
                'message': f'Agent enregistré. Mot de passe généré : {password}',
                'generated_password': password # Utile pour l'afficher à l'admin
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée.'}, status=405)


def recherche_patient(request): 
    query = request.GET.get('q', '').strip()
    
    if query:
        # Testons d'abord avec les champs directs du patient
        patients = Patient.objects.filter(
            Q(nom__icontains=query) | 
            Q(prenom__icontains=query) | 
            Q(code__icontains=query)
        ).distinct()
    else:
        patients = Patient.objects.all().order_by('-id')[:20]
        
    return render(request, 'webpages/partials/patient_list.html', {'patients': patients})


def profile(request):
    return render(request, 'webpages/profile.html')