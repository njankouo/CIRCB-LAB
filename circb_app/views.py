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
        'patients':Patient.objects.filter(status=True)
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
    # Préchargement intelligent des relations imbriquées
    fiches = FicheEchantillon.objects.prefetch_related(
        'echantillons__enfant__fosa',
        'echantillons__mere',
        'echantillons__resultats__test',
        'echantillons__resultats__resultat_pcr'
    ).order_by('-id')[:2]

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
                numero_ordre=numero_ordre,
                date_Envoie_labo = request.POST.get('date_entree_labo')
                
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
            numero_serie = (request.POST.get('numero_serie') or '').strip().upper()
            mere_id = request.POST.get('mere_id')
            
            enfant_id = request.POST.get('enfant_id')
            
           
            # 2. Construction du code de base
            code_patient = f"{code_region}{code_district}{code_fosa}{code_pt}"

            try:
                # 1. Récupération obligatoire de la Fiche
                fiche = FicheEchantillon.objects.filter(id=fiche_id).first() if fiche_id else None
                if not fiche:
                    return JsonResponse({'success': False, 'error': "Fiche d'échantillon introuvable."}, status=400)

                # --- Helpers de nettoyage ---
                def p_bool(val):
                    return str(val).strip().lower() == 'oui' if val else False

                def p_int(val):
                    return int(val) if val and str(val).isdigit() else None

                def p_float(val):
                    if not val: return None
                    try: return float(str(val).replace(',', '.'))
                    except ValueError: return None

                def p_date(val):
                    if not val: return None
                    try: return datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
                    except ValueError: return None

                # --- Transaction Atomique ---
                with transaction.atomic():

                    # -------------------------------------------------------------
                    # 2. PATIENT / ENFANT : Récupération & Mise à Jour des Infos
                    # -------------------------------------------------------------
                    enfant = None
                    if code_patient:
                        enfant = Patient.objects.filter(code=code_patient).first()
                    elif enfant_id:
                        enfant = Patient.objects.filter(id=enfant_id).first()

                    if not enfant:
                        return JsonResponse({'success': False, 'error': f"Le patient avec le code '{code_patient}' est introuvable."}, status=404)

                    # Mise à jour des informations spécifiques de l'enfant
                    if request.POST.get('enfant_nom'):
                        enfant.nom = request.POST.get('enfant_nom', '').strip()
                    if request.POST.get('enfant_prenom'):
                        enfant.prenom = request.POST.get('enfant_prenom', '').strip()
                    if request.POST.get('date_naissance'):
                        enfant.date_naissance = p_date(request.POST.get('date_naissance'))
                    if request.POST.get('sexe'):
                        enfant.sexe = request.POST.get('sexe', '').strip()
                    enfant.status=True
                    
                    enfant.save()

                    # -------------------------------------------------------------
                    # 3. MÈRE : Création ou Mise à Jour des Infos
                    # -------------------------------------------------------------
                    mere = None
                    if mere_id:
                        mere = Mere.objects.filter(id=mere_id).first()

                    # Données Mère envoyées depuis le formulaire
                    nom_mere = request.POST.get('mere_nom', '').strip()
                    prenom_mere = request.POST.get('mere_prenom', '').strip()
                    date_naissance_mere = p_date(request.POST.get('mere_date_naissance'))
                    contact_mere = request.POST.get('contact_familial', '').strip()

                    if not mere:
                        # Si la mère n'existe pas, on la crée si au moins un champ est fourni
                        if nom_mere or prenom_mere or contact_mere:
                            mere = Mere.objects.create(
                                nom=nom_mere,
                                prenom=prenom_mere,
                                date_naissance=date_naissance_mere,
                                contact=contact_mere
                            )
                    else:
                        # Si la mère existe déjà, on met à jour ses coordonnées
                        if nom_mere: mere.nom = nom_mere
                        if prenom_mere: mere.prenom = prenom_mere
                        if date_naissance_mere: mere.date_naissance = date_naissance_mere
                        if contact_mere: mere.contact = contact_mere
                        mere.save()

                    # Association de la mère à l'enfant
                    if mere and hasattr(enfant, 'mere'):
                        enfant.mere = mere
                        enfant.save()

                    # -------------------------------------------------------------
                    # 4. ENREGISTREMENT DE L'ÉCHANTILLON
                    # -------------------------------------------------------------
                    echantillon = Echantillon.objects.create(
                        code = request.POST.get('code_echantillon'),
                        fiche=fiche,
                        enfant=enfant,
                        mere=mere,
                        
                        # INFOS ENFANT (Variables au précompte)
                        rang_naissance=p_int(request.POST.get('rang_naissance')),
                        poids=p_float(request.POST.get('poids')),
                        profilaxie_arv_id=p_int(request.POST.get('profilaxie_arv')),
                        
                        # INFOS SUIVI MÈRE
                        protocole_ptme_id=p_int(request.POST.get('protocole_ptme')),
                        date_rdv=p_date(request.POST.get('date_prochain_rdv')),
                        date_initiation_ptme=p_date(request.POST.get('date_initiation_ptme')),
                        date_diagnostic_vih=p_date(request.POST.get('date_diagnostic_vih')),
                        numero_grossesse=p_int(request.POST.get('numero_grossesse')),
                        nb_enfant_expose=p_int(request.POST.get('nb_enfant_expose')),
                        nb_enfant_infecte=p_int(request.POST.get('nb_enfant_infecte')),
                        mode_accouchement_id=p_int(request.POST.get('mode_accouchement')),
                        date_diagnostic_lav=p_date(request.POST.get('date_diagnostic_lav')),
                        
                        # SUIVI CLINIQUE ET VIROLOGIQUE
                        present_symptome=p_bool(request.POST.get('enfant_symptomatique')),
                        present_allaitement=p_bool(request.POST.get('enfant_allaite')),
                        mode_allaitement_id=p_int(request.POST.get('mode_allaitement')),
                        present_sevrage=p_bool(request.POST.get('statut_sevrage')),
                        date_sevrage=p_date(request.POST.get('date_sevrage')),
                        present_cotrimoxazole=p_bool(request.POST.get('sous_cotrim')),
                        date_cotrimoxazole=p_date(request.POST.get('date_initiation_cotrim')),
                        present_tarv=p_bool(request.POST.get('sous_tarv')),
                        date_tarv=p_date(request.POST.get('date_initiation_tarv')),
                        
                        # PCR ET PRÉLÈVEMENT
                      
                        raison_prelevement_id=p_int(request.POST.get('raisons_prelevement')),
                        
                        date_prelevement=p_date(request.POST.get('date_prelevement')),
                        duplicate_prelevement=p_bool(request.POST.get('duplicate_prelevement')),
                        nom_preleveur=request.POST.get('nom_preleveur', '').strip(),
                        prenom_preleveur=request.POST.get('prenom_preleveur', '').strip(),
                        contact_preleveur=p_int(request.POST.get('contact_preleveur')),
                        observation=request.POST.get('observation', '').strip(),
                        date_enregistrement = datetime.now()
                    )
                
                return JsonResponse({
                    'success': True, 
                    'message': "Les données du patient et de la mère ont été enregistrées avec succès !"
                })

            except Exception as e:
                return JsonResponse({'success': False, 'error': f"Erreur traitement : {str(e)}"}, status=500)
        
        return JsonResponse({'success': False, 'error': "Requête non autorisée."}, status=400)

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
def formater_date(valeur_date):
    """Convertit en toute sécurité une date en chaîne YYYY-MM-DD"""
    if not valeur_date:
        return None
    if hasattr(valeur_date, 'strftime'):
        return valeur_date.strftime('%Y-%m-%d')
    return str(valeur_date)
def verifier_patient(request):
    """Vérifie l'existence d'un patient par son code unique complet"""
    code_recherche = request.GET.get('code', '').strip()
    
    if not code_recherche:
        return JsonResponse({'existe': False, 'erreur': 'Code manquant'}, status=400)
    
    try:
        patient = Patient.objects.filter(code=code_recherche).first()
        
        if not patient:
            return JsonResponse({'existe': False})

        # Données de la mère
        mere_data = None
        mere_obj = getattr(patient, 'mere', None)
        
        if mere_obj:
            # Récupération sécurisée de l'ID du contact
            contact_id = None
            if hasattr(mere_obj, 'contact_id') and mere_obj.contact_id is not None:
                contact_id = mere_obj.contact_id
            elif hasattr(mere_obj, 'contact') and mere_obj.contact is not None:
                contact_id = mere_obj.contact if isinstance(mere_obj.contact, int) else getattr(mere_obj.contact, 'id', None)

            mere_data = {
                'id': mere_obj.id,
                'nom': getattr(mere_obj, 'nom', ''),
                'prenom': getattr(mere_obj, 'prenom', ''),
                'contact': contact_id,
                'age': getattr(mere_obj, 'age', None),
                'date_naissance': formater_date(getattr(mere_obj, 'date_naissance', None)),
            }

        # Données de la porte d'entrée
        porte_entree_id = None
        if hasattr(patient, 'porte_entree_id') and patient.porte_entree_id:
            porte_entree_id = patient.porte_entree_id
        elif hasattr(patient, 'porte_entree') and patient.porte_entree:
            porte_entree_id = patient.porte_entree if isinstance(patient.porte_entree, int) else getattr(patient.porte_entree, 'id', None)

        return JsonResponse({
            'existe': True,
            'patient': {
                'id': patient.id,
                'nom': patient.nom,
                'prenom': patient.prenom,
                'sexe': getattr(patient, 'sexe', None),
                'porte_entree': porte_entree_id,
                'date_naissance': formater_date(getattr(patient, 'date_naissance', None)),
                'mere': mere_data,
            }
        })

    except Exception as e:
        logger.error(f"Erreur lors de la vérification du patient {code_recherche} : {str(e)}", exc_info=True)
        return JsonResponse({
            'existe': False, 
            'erreur': f"Erreur serveur : {str(e)}"
        }, status=500)

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

import base64
import io
import os
from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import get_object_or_404, HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa


def imprimer_resultat_pdf(request, resultat_id):
    resultat = get_object_or_404(Resultat, id=resultat_id)

    # 1. Récupération et conversion du logo en Base64
    logo_base64 = ""
    # Mettez le nom exact de votre fichier (vérifiez la casse : Logo-CIRCB.png ou logo_circb.png)
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find(
        "images/logo_circb.png"
    )

    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Transmission au template
    context = {
        "resultat": resultat,
        "logo_base64": logo_base64,
    }

    html_content = render_to_string(
        "webpages/resultats/resultat_pdf.html", context
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="Resultat_{resultat.id}.pdf"'
    )

    pisa_status = pisa.pisaDocument(
        io.BytesIO(html_content.encode("utf-8")), response, encoding="utf-8"
    )

    if pisa_status.err:
        return HttpResponse("Erreur lors de la compilation du PDF.", status=500)

    return response


def resultats_individuel(request, id):
    resultat = get_object_or_404(Resultat, id=id)

    # 1. Récupération et conversion du logo en Base64 (contourne tout souci de chemin relatif avec xhtml2pdf)
    logo_base64 = ""
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find(
        "images/logo_circb.png"
    )

    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Transmission au template avec la date du jour d'impression
    context = {
        "resultat": resultat,
        "logo_base64": logo_base64,
        "date_impression": timezone.now(),  # Permet d'avoir la date du jour dynamique sur le PDF
    }

    # 3. Rendu du template HTML
    html_content = render_to_string(
        "webpages/rapports/resultat-individuel.html", context
    )

    # 4. Génération du PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="Resultat_{resultat.id}.pdf"'
    )

    pisa_status = pisa.pisaDocument(
        io.BytesIO(html_content.encode("utf-8")), response, encoding="utf-8"
    )

    if pisa_status.err:
        return HttpResponse("Erreur lors de la compilation du PDF.", status=500)

    return response




def resultats_collectifs(request):
   

    # 1. Récupération et conversion du logo en Base64 (contourne tout souci de chemin relatif avec xhtml2pdf)
    logo_base64 = ""
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find(
        "images/logo_circb.png"
    )

    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Transmission au template avec la date du jour d'impression
    context = {
       
        "logo_base64": logo_base64,
        "date_impression": timezone.now(),  # Permet d'avoir la date du jour dynamique sur le PDF
    }

    # 3. Rendu du template HTML
    html_content = render_to_string(
        "webpages/rapports/resultats-collectif.html", context
    )

    # 4. Génération du PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="Resultat.pdf"'
    )

    pisa_status = pisa.pisaDocument(
        io.BytesIO(html_content.encode("utf-8")), response, encoding="utf-8"
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


def formater_date(valeur_date):
    """Convertit en toute sécurité une date en chaîne YYYY-MM-DD"""
    if not valeur_date:
        return None
    if hasattr(valeur_date, 'strftime'):
        return valeur_date.strftime('%Y-%m-%d')
    return str(valeur_date)

def rechercher_patient(request):
    code = request.GET.get('code', '').strip().upper()
    
    if not code:
        return JsonResponse({'exists': False, 'erreur': 'Code manquant'}, status=400)

    try:
        patient = Patient.objects.filter(code=code).first()
        
        if not patient:
            return JsonResponse({'exists': False})

        # --- Construction sécurisée du dictionnaire de la mère ---
        mere_data = None
        mere_obj = getattr(patient, 'mere', None)
        if mere_obj:
            # Récupération sécurisée du contact (gère le cas où contact est déjà un ID int)
            contact_id = None
            if hasattr(mere_obj, 'contact_id') and mere_obj.contact_id is not None:
                contact_id = mere_obj.contact_id
            elif hasattr(mere_obj, 'contact') and mere_obj.contact is not None:
                contact_id = mere_obj.contact if isinstance(mere_obj.contact, int) else getattr(mere_obj.contact, 'id', None)

            mere_data = {
                'id': mere_obj.id,
                'nom': getattr(mere_obj, 'nom', ''),
                'prenom': getattr(mere_obj, 'prenom', ''),
                'contact': contact_id,
                'age': getattr(mere_obj, 'age', None),
                'date_naissance': formater_date(getattr(mere_obj, 'date_naissance', None)),
            }

        # --- Construction sécurisée de la porte d'entrée ---
        porte_entree_id = None
        if hasattr(patient, 'porte_entree_id') and patient.porte_entree_id is not None:
            porte_entree_id = patient.porte_entree_id
        elif hasattr(patient, 'porte_entree') and patient.porte_entree is not None:
            porte_entree_id = patient.porte_entree if isinstance(patient.porte_entree, int) else getattr(patient.porte_entree, 'id', None)

        return JsonResponse({
            'exists': True,
            'patient': {
                'id': patient.id,
                'code': patient.code,
                'nom': patient.nom,
                'prenom': patient.prenom,
                'sexe': getattr(patient, 'sexe', None),
                'porte_entree': porte_entree_id,
                'date_naissance': formater_date(getattr(patient, 'date_naissance', None)),
                'mere': mere_data,
            }
        })

    except Exception as e:
        logger.error(f"Erreur recherche patient {code} : {str(e)}", exc_info=True)
        return JsonResponse({'exists': False, 'erreur': f"Erreur serveur : {str(e)}"}, status=500)



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

def define_plage(request):
    return render(request, 'webpages/resultats/plages.html')


def liste_echantillon(request):
    if request.method=="POST":
       pass

def statistic_echantillon(request):
    # 1. QuerySet de base
    echantillons = Echantillon.objects.all()

    # 2. Filtre par FOSA (sélectionné dans la modale HTML)
    fosa = request.GET.get('fosa')
    if fosa:
        echantillons = echantillons.filter(fosa=fosa)

    # 3. Récupération de la période et de l'année
    periode_type = request.GET.get('periode_type', 'toutes')
    annee_val = request.GET.get('annee')
    annee = (
        int(annee_val) if annee_val and annee_val.isdigit() else datetime.now().year
    )

    # 4. Filtres temporels (On conserve un QuerySet à chaque étape)
    if periode_type == 'journalier':
        date_jour = request.GET.get('date_jour')
        if date_jour:
            # ✅ Pas de __date sur un DateField
            echantillons = echantillons.filter(date_enregistrement=date_jour)

    elif periode_type == 'mensuel':
        mois_raw = request.GET.get('mois')  # Format YYYY-MM
        if mois_raw and '-' in mois_raw:
            year, month = mois_raw.split('-')
            echantillons = echantillons.filter(
                date_enregistrement__year=year, date_enregistrement__month=month
            )

    elif periode_type == 'trimestriel':
        trimestre_val = request.GET.get('trimestre', '1')
        trimestre = int(trimestre_val) if trimestre_val.isdigit() else 1
        echantillons = echantillons.filter(
            date_enregistrement__year=annee,
            date_enregistrement__quarter=trimestre,
        )

    elif periode_type == 'semestriel':
        semestre = request.GET.get('semestre', 'S1')
        mois_semestre = range(1, 7) if semestre == 'S1' else range(7, 13)
        echantillons = echantillons.filter(
            date_enregistrement__year=annee,
            date_enregistrement__month__in=mois_semestre,
        )

    elif periode_type == 'annuel':
        echantillons = echantillons.filter(date_enregistrement__year=annee)

    elif periode_type == 'custom':
        date_debut = request.GET.get('date_debut')
        date_fin = request.GET.get('date_fin')
        if date_debut and date_fin:
            # ✅ __range direct sur DateField
            echantillons = echantillons.filter(
                date_enregistrement__range=[date_debut, date_fin]
            )
        elif date_debut:
            echantillons = echantillons.filter(
                date_enregistrement__gte=date_debut
            )
        elif date_fin:
            echantillons = echantillons.filter(
                date_enregistrement__lte=date_fin
            )

    # 5. Calcul du total après filtrage
    total_echantillons = echantillons.count()

    return render(
        request,
        'webpages/dashbord_hosp.html',
        {
            'echantillons': echantillons,  # QuerySet filtré (pour boucler dessus)
            'total_echantillons': total_echantillons,  # Entier pour afficher la métrique
        },
    )

@require_POST
def save_code_patient(request):
    codes_enregistres = []
    codes_existants = []

    # 1. Parcourir tous les champs envoyés dans le POST
    for key, value in request.POST.items():
        if key.startswith('code_patient') and value.strip():
            code = value.strip()
            
            # 2. Vérifier si le code existe déjà en BDD
            if Patient.objects.filter(code=code).exists():
                codes_existants.append(code)
            else:
                Patient.objects.create(code=code)
                codes_enregistres.append(code)

    # Si aucun champ n'était rempli dans le formulaire
    if not codes_enregistres and not codes_existants:
        return JsonResponse({
            'status': 'error',
            'message': 'Aucun code valide n\'a été fourni.'
        }, status=400)

    # 3. Réponse JSON alignée avec le modal JS
    return JsonResponse({
        'status': 'success',
        'message': 'Traitement effectué.',
        'codes_initialises': codes_enregistres,  # 👈 Aligné avec le JS
        'codes_refuses': codes_existants        # 👈 Aligné avec le JS
    }, status=200)


from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from .models import Echantillon, ResultatPcr, Test


def search_plage(request):
    tests = Test.objects.all()
    resultats_pcr = ResultatPcr.objects.all()

    echantillons = None
    selected_test_id = request.POST.get('test_id', '').strip()
    selected_resultat_pcr_id = request.POST.get('resultat_pcr_id', '').strip()
    debut_raw = request.POST.get('debut_ancien_code', '').strip()
    fin_raw = request.POST.get('fin_code_echantillon', '').strip()
    exclure_raw = request.POST.get('liste_exclure', '').strip()
    inclusion_raw = request.POST.get('liste_inclure', '').strip()

    if request.method == 'POST':

        # -------------------------------------------------------------
        # 1. ACTION : ENREGISTREMENT / ATTRIBUTION DES RÉSULTATS
        # -------------------------------------------------------------
        if 'save_results' in request.POST:
            echantillons_ids = request.POST.getlist('echantillon_ids')
            count_updated = 0

            for ech_id in echantillons_ids:
                res_id = request.POST.get(f'resultat_{ech_id}', '').strip()
                test_id_item = request.POST.get(f'test_{ech_id}', '').strip()

                try:
                    ech = Echantillon.objects.get(id=ech_id)

                    # Mise à jour du résultat PCR
                    ech.resultat_pcr_id = int(res_id) if res_id else None

                    # Mise à jour du test si sélectionné
                    ech.test_id = int(test_id_item) if test_id_item else None

                    ech.save()
                    count_updated += 1
                except Echantillon.DoesNotExist:
                    continue

            messages.success(
                request,
                f' {count_updated} résultat(s) d\'échantillon(s) mis à jour avec succès !',
            )

        # -------------------------------------------------------------
        # 2. ACTION : FILTRAGE / RECHERCHE DES ÉCHANTILLONS
        # -------------------------------------------------------------
        debut = int(debut_raw) if debut_raw.isdigit() else None
        fin = int(fin_raw) if fin_raw.isdigit() else None

        liste_exclure = [
            int(i.strip())
            for i in exclure_raw.replace('\n', ',').split(',')
            if i.strip().isdigit()
        ]
        liste_inclure = [
            int(i.strip())
            for i in inclusion_raw.replace('\n', ',').split(',')
            if i.strip().isdigit()
        ]

        query_plage = Q()
        if debut is not None and fin is not None:
            query_plage |= Q(code__gte=debut, code__lte=fin)
        elif debut is not None:
            query_plage |= Q(code__gte=debut)
        elif fin is not None:
            query_plage |= Q(code__lte=fin)

        query_totale = query_plage
        if liste_inclure:
            query_totale |= Q(code__in=liste_inclure)

        if query_totale:
            echantillons = Echantillon.objects.filter(query_totale)
        elif debut is None and fin is None and not liste_inclure:
            echantillons = Echantillon.objects.all()
        else:
            echantillons = Echantillon.objects.none()

        if liste_exclure and echantillons.exists():
            echantillons = echantillons.exclude(code__in=liste_exclure)

        if selected_test_id and echantillons.exists():
            echantillons = echantillons.filter(test_id=selected_test_id)

        if selected_resultat_pcr_id and echantillons.exists():
            echantillons = echantillons.filter(
                resultat_pcr_id=selected_resultat_pcr_id
            )

        if echantillons.exists():
            echantillons = (
                echantillons.select_related('enfant', 'test', 'resultat_pcr')
                .distinct()
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
        'echantillons': echantillons,
    }

    return render(request, 'webpages/resultats/plages.html', context)






@login_required
def save_plage(request):
    echantillons = []
    
    # 1. Récupération des paramètres de filtrage (POST ou GET)
    debut = request.POST.get('debut_ancien_code') or request.GET.get('debut_ancien_code', '')
    fin = request.POST.get('fin_code_echantillon') or request.GET.get('fin_code_echantillon', '')
    inclure_raw = request.POST.get('liste_inclure') or request.GET.get('liste_inclure', '')
    exclure_raw = request.POST.get('liste_exclure') or request.GET.get('liste_exclure', '')

    # Helper interne pour nettoyer les listes de codes saisies manuellement (ex: "101, 102\n103")
    def parse_code_list(raw_string):
        if not raw_string:
            return []
        cleaned = raw_string.replace('\r', '').replace('\n', ',')
        return [c.strip() for c in cleaned.split(',') if c.strip()]

    codes_inclure = parse_code_list(inclure_raw)
    codes_exclure = parse_code_list(exclure_raw)

    # 2. TRAITEMENT DE L'ENREGISTREMENT DES RÉSULTATS (Soumission du Formulaire)
    if request.method == 'POST' and 'save_results' in request.POST:
        echantillon_ids = request.POST.getlist('echantillon_ids')
        saved_count = 0

        # Utilisation d'une transaction atomique pour assurer la rapidité et la sécurité
        with transaction.atomic():
            for ech_id in echantillon_ids:
                test_id = request.POST.get(f'test_{ech_id}') or None
                resultat_pcr_id = request.POST.get(f'resultat_{ech_id}') or None

                # On enregistre ou met à jour si au moins une valeur est sélectionnée
                if test_id or resultat_pcr_id:
                    Resultat.objects.update_or_create(
                        echantillon_id=ech_id,
                        defaults={
                            'test_id': test_id,
                            'resultat_pcr_id': resultat_pcr_id,
                            'responsable': request.user,
                            'date_resultat': datetime.now()
                        }
                    )
                    
                    # (Optionnel) Si ton modèle Echantillon conserve aussi le résultat direct :
                    Echantillon.objects.filter(id=ech_id).update(
                        test_id=test_id, 
                        resultat_pcr_id=resultat_pcr_id
                    )
                    
                    saved_count += 1

        messages.success(request, f" {saved_count} résultat(s) enregistré(s) avec succès !")

    # 3. RECHERCHE ET EXTRACTION DES ÉCHANTILLONS
    if debut or fin or codes_inclure:
        query = Q()

        # Plage numérique / alphabétique de codes
        if debut and fin:
            # On suppose que `code` contient une valeur numérique ou qu'un champ `ancien_code` est utilisé
            query |= Q(code__gte=debut, code__lte=fin)

        # Ajout des codes spécifiques à inclure
        if codes_inclure:
            query |= Q(code__in=codes_inclure)

        # Récupération de la liste filtrée
        queryset = Echantillon.objects.filter(query).select_related('enfant')

        # Exclusion des codes spécifiés
        if codes_exclure:
            queryset = queryset.exclude(code__in=codes_exclure)

        echantillons = queryset.order_by('code')

    # 4. CHARGEMENT DES LISTES POUR LES SELECTS
    tests = Test.objects.all()
    resultats_pcr = ResultatPcr.objects.all()

    context = {
        'echantillons': echantillons,
        'tests': tests,
        'resultats_pcr': resultats_pcr,
        'debut': debut,
        'fin': fin,
        'inclusion': inclure_raw,
        'exclure': exclure_raw,
    }
    messages.success(request, 'Resultats Valides avec succes')
    return render(request, 'webpages/resultats/plages.html', context)




