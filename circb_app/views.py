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
from .decorators import role_required
# 1. On garde l'import de Django sous un autre nom ou on importe ton fichier models local
from .models import Structure_Hierachy, Structure 
# Create your views here.
def connexion_view(request):
    # Django ira chercher ce fichier dans vos dossiers de templates configurés
    return render(request, 'webpages/login_hosp.html')

@login_required(login_url='/')
def dashboard(request):
    context={
        'fosas_niveau_3': Structure.objects.filter(hierachy__rang=2)
    }
    return render(request, 'webpages/dashbord_hosp.html', context)
@login_required(login_url='/')
def personnel(request):
    context ={
        'user':User.objects.all(),
        'role':Role.objects.all(),
        'groupes': Group.objects.all()
      
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
    request.session.flush()
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
@permission_required('circb_app.peut_voir_fiches_expedition', raise_exception=True)
@login_required(login_url='/')
def fiches_echantillons(request):
    dernier_numero= FicheEchantillon.objects.order_by('-numero_ordre').first()
    prochain_numero= (dernier_numero.numero_ordre + 1) if dernier_numero else 1
    context={
        'regions':Structure.objects.filter(parent__isnull=True).order_by('nom'),
        'transporteurs':Transporteur.objects.all().order_by('nom'),
        'moyens_transport':MoyenTransport.objects.all().order_by('nom'),
        'fiches':FicheEchantillon.objects.filter(status=True).order_by('-id'),
        'dernier_numero':dernier_numero,
        'prochain_numero': prochain_numero,
        'fichescount':FicheEchantillon.objects.filter(status=False).count(),
        'fiche_enable':FicheEchantillon.objects.filter(status=False)[:8],
      
        
    }
    return render(request, 'webpages/echantillonages/fiche_echantillons.html', context)
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
@login_required(login_url='/')
def echantillonages(request):
    # Préchargement intelligent des relations imbriquées
    fiches = FicheEchantillon.objects.prefetch_related(
        'echantillons__enfant__fosa',
        'echantillons__mere',
        'echantillons__resultats__test',
        'echantillons__resultats__resultat_pcr'
    ).order_by('-id')

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
            mere_id = request.POST.get('mere_id')
            enfant_id = request.POST.get('enfant_id')
            
            try:
                instance_test = Test.objects.get(id=request.POST.get('examen'))
            except Test.DoesNotExist:
                return JsonResponse({'success': False, 'error': "Examen introuvable."}, status=400)
           
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

                # --- Récupération des données pour validation préalable ---
                poids = p_float(request.POST.get('poids'))
                date_naissance_enfant = p_date(request.POST.get('date_naissance'))
                date_initiation_tarv = p_date(request.POST.get('date_initiation_tarv'))
                date_sevrage = p_date(request.POST.get('date_sevrage'))
                date_naissance_mere = p_date(request.POST.get('mere_date_naissance'))

                # --- VALIDATIONS MÉTIER STRICTES ---
                
                # 1. Le poids doit être supérieur ou égal à 6 kg
                if poids is not None and poids < 6:
                    return JsonResponse({'success': False, 'error': "Le poids de l'échantillon/enfant doit être supérieur ou égal à 6 kg."}, status=400)

                # 2. La date d'initiation TARV doit être supérieure à la date de naissance de l'enfant
                if date_initiation_tarv and date_naissance_enfant:
                    if date_initiation_tarv <= date_naissance_enfant:
                        return JsonResponse({'success': False, 'error': "La date d'initiation TARV doit être strictement supérieure à la date de naissance de l'enfant."}, status=400)

                # 3. La date de naissance de l'enfant doit être inférieure à la date de sevrage
                if date_naissance_enfant and date_sevrage:
                    if date_naissance_enfant >= date_sevrage:
                        return JsonResponse({'success': False, 'error': "La date de naissance de l'enfant doit être inférieure à la date de sevrage."}, status=400)

                # 4 & 5. Règles sur l'âge de la mère et comparaison avec l'enfant
                if date_naissance_mere:
                    # Âge minimum de la mère : >= 11 ans (on approxime en comparant les années ou jours)
                    # 11 ans en jours ~= 11 * 365.25 jours
                    age_mere_jours = (datetime.now().date() - date_naissance_mere).days
                    if age_mere_jours < (11 * 365):
                        return JsonResponse({'success': False, 'error': "L'âge de la mère doit être supérieur ou égal à 11 ans."}, status=400)

                    # L'enfant ne doit pas être plus âgé que la mère
                    if date_naissance_enfant and date_naissance_mere >= date_naissance_enfant:
                        return JsonResponse({'success': False, 'error': "Incohérence : L'enfant ne peut pas être plus âgé (ou né avant) que sa mère."}, status=400)


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

                    if request.POST.get('enfant_nom'):
                        enfant.nom = request.POST.get('enfant_nom', '').strip()
                    if request.POST.get('enfant_prenom'):
                        enfant.prenom = request.POST.get('enfant_prenom', '').strip()
                    if date_naissance_enfant:
                        enfant.date_naissance = date_naissance_enfant
                    if request.POST.get('sexe'):
                        enfant.sexe = request.POST.get('sexe', '').strip()
                    enfant.status = True
                    enfant.save()

                    # -------------------------------------------------------------
                    # 3. MÈRE : Création ou Mise à Jour des Infos
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
                        code = request.POST.get('code_echantillon'),
                        fiche=fiche,
                        enfant=enfant,
                        mere=mere,
                        
                        # INFOS ENFANT
                        rang_naissance=p_int(request.POST.get('rang_naissance')),
                        poids=poids,
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
                        test = instance_test,
                        
                        # SUIVI CLINIQUE ET VIROLOGIQUE
                        present_symptome=p_bool(request.POST.get('enfant_symptomatique')),
                        present_allaitement=p_bool(request.POST.get('enfant_allaite')),
                        mode_allaitement_id=p_int(request.POST.get('mode_allaitement')),
                        present_sevrage=p_bool(request.POST.get('statut_sevrage')),
                        date_sevrage=date_sevrage,
                        present_cotrimoxazole=p_bool(request.POST.get('sous_cotrim')),
                        date_cotrimoxazole=p_date(request.POST.get('date_initiation_cotrim')),
                        present_tarv=p_bool(request.POST.get('sous_tarv')),
                        date_tarv=date_initiation_tarv,
                        
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
def update_echantillon(request, id):
    echantillon = get_object_or_404(Echantillon, id=id)
    
    if request.method == 'POST':
        try:
            # Fonctions utilitaires intégrées directement pour éviter les erreurs
            raw_poids = request.POST.get('poids')
            poids = float(raw_poids.replace(',', '.')) if raw_poids and str(raw_poids).strip() != '' else None

            def parse_date(val):
                if val and str(val).strip() != '':
                    try:
                        return datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
                    except ValueError:
                        return None
                return None

            def parse_int(val):
                try:
                    return int(val) if val and str(val).strip() != '' else None
                except (ValueError, TypeError):
                    return None

            def parse_bool(val):
                return val in [True, 'on', 'true', '1', 'True']

            # Récupération des données converties
            date_naissance_enfant = parse_date(request.POST.get('date_naissance'))
            date_initiation_tarv = parse_date(request.POST.get('date_initiation_tarv'))
            date_sevrage = parse_date(request.POST.get('date_sevrage'))
            date_naissance_mere = parse_date(request.POST.get('mere_date_naissance'))
            
            # --- VALIDATIONS MÉTIER STRICTES ---
            
            # 1. Le poids doit être supérieur ou égal à 6 kg
            if poids is not None and poids < 6:
                messages.error(request, "Le poids de l'échantillon/enfant doit être supérieur ou égal à 6 kg.")
                return redirect('update_echantillon', id=echantillon.id)
            
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
            echantillon.code = request.POST.get('code_echantillon', echantillon.code)
            
            # INFOS ENFANT
            echantillon.rang_naissance = parse_int(request.POST.get('rang_naissance'))
            echantillon.poids = poids
            echantillon.profilaxie_arv_id = parse_int(request.POST.get('profilaxie_arv'))
            
            # INFOS SUIVI MÈRE
            echantillon.protocole_ptme_id = parse_int(request.POST.get('protocole_ptme'))
            echantillon.date_rdv = parse_date(request.POST.get('date_prochain_rdv'))
            echantillon.date_initiation_ptme = parse_date(request.POST.get('date_initiation_ptme'))
            echantillon.date_diagnostic_vih = parse_date(request.POST.get('date_diagnostic_vih'))
            echantillon.numero_grossesse = parse_int(request.POST.get('numero_grossesse'))
            echantillon.nb_enfant_expose = parse_int(request.POST.get('nb_enfant_expose'))
            echantillon.nb_enfant_infecte = parse_int(request.POST.get('nb_enfant_infecte'))
            echantillon.mode_accouchement_id = parse_int(request.POST.get('mode_accouchement'))
            echantillon.date_diagnostic_lav = parse_date(request.POST.get('date_diagnostic_lav'))
            
           
            
            
            
            # SUIVI CLINIQUE ET VIROLOGIQUE
            echantillon.present_symptome = parse_bool(request.POST.get('enfant_symptomatique'))
            echantillon.present_allaitement = parse_bool(request.POST.get('enfant_allaite'))
            echantillon.mode_allaitement_id = parse_int(request.POST.get('mode_allaitement'))
            echantillon.present_sevrage = parse_bool(request.POST.get('statut_sevrage'))
            echantillon.date_sevrage = date_sevrage
            echantillon.present_cotrimoxazole = parse_bool(request.POST.get('sous_cotrim'))
            echantillon.date_cotrimoxazole = parse_date(request.POST.get('date_initiation_cotrim'))
            echantillon.present_tarv = parse_bool(request.POST.get('sous_tarv'))
            echantillon.date_tarv = date_initiation_tarv
            
            # PCR ET PRÉLÈVEMENT
            echantillon.raison_prelevement_id = parse_int(request.POST.get('raisons_prelevement'))
            echantillon.date_prelevement = parse_date(request.POST.get('date_prelevement'))
            echantillon.duplicate_prelevement = parse_bool(request.POST.get('is_reprelevement'))
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

from django.http import JsonResponse
from django.template.loader import render_to_string
from django.http import JsonResponse

def formater_date(valeur_date):
    """Convertit en toute sécurité une date en chaîne YYYY-MM-DD"""
    if not valeur_date:
        return None
    if hasattr(valeur_date, 'strftime'):
        return valeur_date.strftime('%Y-%m-%d')
    return str(valeur_date)

def verifier_patient(request):
    """Vérifie l'existence d'un patient par son code unique complet et récupère ses antécédents d'échantillons"""
    code_recherche = request.GET.get('code', '').strip()
    
    if not code_recherche:
        return JsonResponse({'existe': False, 'erreur': 'Code manquant'}, status=400)
    
    try:
        patient = Patient.objects.filter(code=code_recherche).first()
        
        if not patient:
            return JsonResponse({'existe': False})

        # --- RÉCUPÉRATION DES ANCIENS ÉCHANTILLONS / RÉSULTATS DU PATIENT ---
        echantillons_precedents = Echantillon.objects.filter(enfant=patient).order_by('-ordre')
        
        historique_html = render_to_string('webpages/echantillonages/historique_items.html', {
            'historique_echantillons': echantillons_precedents
        }, request=request)

        # Données de la mère
        mere_data = None
        mere_obj = getattr(patient, 'mere', None)
        
        if mere_obj:
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
                'historique_html': historique_html  # <-- Corrigé ici : renvoie bien le HTML généré
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

def resultats(request):
    resultats=Resultat.objects.filter(resultat_pcr__isnull=False).order_by('-date_resultat')
    for res in resultats:
        code_str = str(res.echantillon.code)
        res.qr_code_svg = generer_qr_svg(code_str)
    context ={
        'resultats': resultats
       
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

import base64
import os
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

def resultats_individuel(request, id):
    resultat = get_object_or_404(Resultat, id=id)

    # 1. Récupération et conversion du logo en Base64
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
        'responsable': request.user,  # Ajout de l'utilisateur connecté comme responsable
        "logo_base64": logo_base64,
        "date_impression": timezone.now(),
    }

    # 3. Rendu du template HTML
    html_content = render_to_string(
        "webpages/rapports/resultat-individuel.html", context
    )

    # 4. Génération du PDF avec WeasyPrint
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="Resultat_{resultat.id}.pdf"'
    )

    # WeasyPrint prend directement la chaîne HTML et écrit dans la réponse HTTP
    HTML(string=html_content, base_url=request.build_absolute_uri()).write_pdf(response)

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
        "date_impression": timezone.now(), 
        "resultats":Resultat.objects.filter(resultat_pcr__isnull=False).order_by('-date_resultat'),
        'responsable': request.user,  # Ajout de l'utilisateur connecté comme responsable
     
    
       
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
    context={
        'now':datetime.now()
    }
    return render(request, 'webpages/resultats/plages.html',context)


def liste_echantillon(request):
    if request.method=="POST":
       pass

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
                            'date_resultat': request.POST.get('date_resultat'),
                            
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
    return redirect('/resultats/')



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
    # 1. Récupération du contexte de base (contient 'actual_institution')
    
    template = 'webpages/config/update-structure.html'
    
    # 2. Récupération sécurisée de la structure à modifier
    structure = get_object_or_404(Structure, id=int(id))
 
    
    # 3. Enrichissement du contexte sans écraser le contenu de basis(request)
    context={
        'structure': structure,
        # Récupère tous les niveaux hiérarchiques de l'institution actuelle
        'hierachie': Structure_Hierachy.objects.order_by('rang'),
        # REQUIS PAR LE TEMPLATE : Toutes les structures pour la liste des parents potentiels
        'all_structures': Structure.objects.all()
    }
    
    return render(request, template, context)




def UpdateDataStructure(request, id):
    if request.method == 'POST':
        # 1. Récupération sécurisée de la structure à modifier
        structure = get_object_or_404(Structure, id=int(id))
        
        # 2. Récupération des données du formulaire POST
        parent_id = request.POST.get('parent_id')
        level_id = request.POST.get('level_id')
        nom = request.POST.get('nom')
        designation = request.POST.get('designation')
        
        try:
            # 3. Mise à jour du Niveau (Hierarchy) - Obligatoire
            if level_id:
                structure.hierachy = get_object_or_404(Structure_Hierachy, id=int(level_id))
            
            # 4. Mise à jour du Parent - Optionnel (vide = unité racine)
            if parent_id and int(parent_id) != structure.id:
                structure.parent = get_object_or_404(Structure, id=int(parent_id))
            else:
                structure.parent = None  # Devient une unité racine
            
            # 5. Mise à jour des champs textuels
            structure.nom = nom
            structure.designation = designation
            
            # 6. Enregistrement en base de données
            structure.save()
            
            # 7. Message de succès et redirection
            messages.success(request, f"L'unité '{nom}' a été modifiée avec succès.")
            return redirect('/structures/') # Ajustez l'URL de redirection selon vos besoins
            
        except Exception as e:
            # Gestion des erreurs imprévues
            messages.error(request, f"Une erreur est survenue lors de la modification : {str(e)}")
            return redirect(request.META.get('HTTP_REFERER', '/'))
            
    # Si la méthode n'est pas POST, on redirige vers la page précédente
    return redirect(request.META.get('HTTP_REFERER', '/'))



def imprimer_resultat_pdf(request):
    # 1. Récupération des paramètres de filtrage GET
    fosa_id = request.session.get('fosa')
    date_debut =  request.session.get('date_debut')
    date_fin =  request.session.get('date_fin')
      
    # 2. Récupération et conversion du logo en Base64
    logo_base64 = ""
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find("images/logo_circb.png")

    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 3. ÉTAPE 1 : Filtrer pour trouver les enfants concernés par la période/FOSA
    base_queryset = Echantillon.objects.all()

    if fosa_id and fosa_id != 'ALL':
        base_queryset = base_queryset.filter(fiche__fosa_id=fosa_id)

    if date_debut:
        base_queryset = base_queryset.filter(date_prelevement__gte=date_debut)
    if date_fin:
        base_queryset = base_queryset.filter(date_prelevement__lte=date_fin)

    enfants_ids = base_queryset.exclude(enfant__isnull=True).values_list('enfant_id', flat=True).distinct()
    echantillons_sans_enfant = base_queryset.filter(enfant__isnull=True).values_list('id', flat=True)

    # 4. ÉTAPE 2 : Récupérer TOUS les échantillons de ces enfants
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

    # 5. ÉTAPE 3 : Grouper les échantillons par Enfant
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

    # 6. ÉTAPE 4 : Mapper les prélèvements selon leur attribut 'ordre' (PCR I, II, III)
    lignes_collectives = []

    for cle_pivot, echos in patients_samples.items():
        row_data = patients_info[cle_pivot].copy()
        row_data.update({
            'pcr1': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_res': '-'},
            'pcr2': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_res': '-'},
            'pcr3': {'date_prel': '-', 'statut': '-', 'code_statut': '', 'date_res': '-'},
        })

        for ech in echos:
            statut_nom = ech.resultat_pcr.nom if ech.resultat_pcr else "EN ATTENTE"
            statut_code = ech.resultat_pcr.code if ech.resultat_pcr else ""
            date_res = "-"

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

            if ech.ordre == 1:
                row_data['pcr1'] = donnees_pcr
            elif ech.ordre == 2:
                row_data['pcr2'] = donnees_pcr
            elif ech.ordre == 3:
                row_data['pcr3'] = donnees_pcr

        lignes_collectives.append(row_data)

    # 7. Transmission au contexte complet du PDF
    context = {
        'lignes_collectives': lignes_collectives,
        'date_debut': date_debut or '',
        'date_fin': date_fin or '',
        'fosa_nom_affiche': fosa_nom_affiche,
        'logo_base64': logo_base64,
    }

    html_content = render_to_string("webpages/rapports/resultat_pdf.html", context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="Resultat.pdf"'

    pisa_status = pisa.pisaDocument(
        io.BytesIO(html_content.encode("utf-8")), response, encoding="utf-8"
    )

    if pisa_status.err:
        return HttpResponse("Erreur lors de la compilation du PDF.", status=500)

    return response


def modifier_fiche_echantillon(request, id):
    fiche = get_object_or_404(FicheEchantillon, id=id)
    
    if request.method == 'POST':
        try:
            # Récupération et mise à jour des champs de la fiche
            fiche.date_enregistrement = request.POST.get('date_enregistrement')
            
            # Localisation (Assurez-vous que les foreignkeys s'attachent par ID)
            fosa_id = request.POST.get('fosa')
            if fosa_id:
                fiche.fosa_id = fosa_id
                
            fiche.expediteur = request.POST.get('expediteur')
            fiche.date_expedition = request.POST.get('date_expedition')
            fiche.nombre_echantillon = request.POST.get('nombre_echantillon')
           
           
            
            transporteur_id = request.POST.get('transporteur')
            if transporteur_id:
                fiche.transporteur_id = transporteur_id
                
            moyen_id = request.POST.get('moyen_transport')
            if moyen_id:
                fiche.moyen_transport_id = moyen_id
                
            fiche.date_reception = request.POST.get('date_reception')
            fiche.date_Envoie_labo = request.POST.get('date_entree_labo')
            fiche.observation = request.POST.get('observation')
            
            fiche.save()
            
            messages.success(request, f"La fiche d'expédition {fiche.code} a été mise à jour avec succès.")
            return redirect('/fiches-echantillons/') # Remplacez par le nom de votre route de redirection
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification : {stratif(e) if 'stratif' in globals() else e}")
            
    return redirect('/fiches-echantillons/')


def modifier_fiche(request, id):
    fiche = get_object_or_404(FicheEchantillon, id=id)
    
    context = {
        'fiche': fiche,
        'regions': Structure.objects.filter(parent__isnull=True),
        'transporteurs': Transporteur.objects.all(), # Adaptez selon vos modèles réels
        'moyens_transport': MoyenTransport.objects.all(), # Adaptez selon vos modèles réels
    }
    return render(request, 'webpages/echantillonages/edit-fiche.html', context)


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

def delete_resultat(request, id):
    resultat = get_object_or_404(Resultat, id=id)
    
    # Récupérer l'échantillon associé et réinitialiser son champ resultat_pcr
    if resultat.echantillon:
        echantillon = resultat.echantillon
        echantillon.resultat_pcr = None
        echantillon.save()
            
    # Suppression du résultat
    resultat.delete()
    
    messages.success(request, "Le résultat a été supprimé avec succès.")
    return redirect(request.META.get('HTTP_REFERER', '/'))


from django.contrib.auth.models import Group, Permission
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