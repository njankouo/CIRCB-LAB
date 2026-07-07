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
    return render(request, 'webpages/personnel.html')


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
    return render(request, 'webpages/patients/dossiers.html')

@login_required(login_url='/')
def configurations(request):
    return render(request, 'webpages/config/configurations.html')
@login_required(login_url='/')
def fiches_echantillons(request):
    context={
        'regions':Structure.objects.filter(parent__isnull=True).order_by('nom'),
        'transporteurs':Transporteur.objects.all().order_by('nom'),
        'moyens_transport':MoyenTransport.objects.all().order_by('nom'),
        'fiches':FicheEchantillon.objects.all().order_by('-date_reception')
    }
    return render(request, 'webpages/echantillonages/fiche_echantillons.html', context)
@login_required(login_url='/')
def echantillons(request):
    context={
        'fiches_echantillon':FicheEchantillon.objects.all().order_by('-date_reception'),
        'tests':Test.objects.all().order_by('nom'),
        'raisons_prelevement':RaisonPrelevement.objects.all().order_by('nom'),
        'modes_allaitement':ModeAllaitement.objects.all().order_by('nom'),
        'resultats_pcr':ResultatPcr.objects.all().order_by('nom')
    }
    return render(request, 'webpages/echantillonages/echantillons.html', context)
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
    """Récupère les districts liés à une région"""
    districts = Structure.objects.filter(parent_id=region_id).values('id', 'nom').order_by('nom')
    # Clé 'districts' exigée par le JavaScript (data.districts)
    return JsonResponse({'districts': list(districts)})

def search_fosa(request, district_id):
    """Récupère les FOSAs liées à un district"""
    fosa_list = Structure.objects.filter(parent_id=district_id).values('id', 'nom').order_by('nom')
    # Clé 'fosas' exigée par le JavaScript (data.fosas)
    return JsonResponse({'fosas': list(fosa_list)})



def search_contact(request, contact_id):
    """
    Récupère le numéro de téléphone d'un transporteur spécifique.
    """
    # get_object_or_404 renvoie une erreur 404 propre si l'ID n'existe pas en BDD
    transporter = get_object_or_404(Transporteur, id=contact_id)
    
    # On renvoie directement un dictionnaire simple avec la clé 'tel'
    return JsonResponse({'tel': transporter.tel})

def enregistrer_fiche_echantillon(request):
    if request.method == "POST":
        # 1. Récupération des données du formulaire
        region_id = request.POST.get('region')
        district_id = request.POST.get('district')
        fosa_id = request.POST.get('fosa')
        transporteur_id = request.POST.get('transporteur')
        moyen_id = request.POST.get('moyen_transport')
        receptioniste_id = request.POST.get('receptioniste')
        
        date_reception = request.POST.get('date_reception')
        date_expedition = request.POST.get('date_expedition')
        nombre_echantillon = request.POST.get('nombre_echantillon')
        observation = request.POST.get('observation')

        # 2. Sécurité : Nettoyage des chaînes vides pour les clés étrangères optionnelles
        # Si l'utilisateur n'a rien choisi, on passe None plutôt qu'une chaîne vide ""
        transporteur_id = transporteur_id if transporteur_id else None
        moyen_id = moyen_id if moyen_id else None

        # 3. Validation des champs obligatoires non négociables
        if not all([region_id, district_id, fosa_id, receptioniste_id, date_reception, date_expedition, nombre_echantillon]):
            return JsonResponse({
                'success': False, 
                'errors': 'Certains champs obligatoires (*) n\'ont pas été transmis.'
            }, status=400)

        try:
            # 4. Création de la fiche
            fiche = FicheEchantillon(
                code=str(uuid.uuid4())[:8].upper(),
                region_id=region_id,
                district_id=district_id,
                fosa_id=fosa_id,
                transporteur_id=transporteur_id,
                moyen_transport_id=moyen_id,
                receptioniste_id=receptioniste_id,
                date_reception=date_reception,
                date_expedition=date_expedition,
                nombre_echantillon=nombre_echantillon,
                observation=observation
            )
            fiche.save()

            return JsonResponse({
                'success': True, 
                'message': f'La fiche {fiche.code} a été enregistrée avec succès !'
            })

        except IntegrityError as e:
            # Cette erreur se déclenche si un ID n'existe pas dans vos tables Structure, Personnel, etc.
            print(f"Erreur d'intégrité BDD : {e}")
            return JsonResponse({
                'success': False, 
                'errors': "Erreur d'association (Clé étrangère introuvable). Vérifiez que les sélections (Région/District/FOSA/Personnel) existent bien en base de données."
            }, status=400)
            
        except Exception as e:
            return JsonResponse({'success': False, 'errors': str(e)}, status=500)

    return JsonResponse({'success': False, 'errors': 'Méthode non autorisée.'}, status=405)


def details_fiche(request, slug):
    fiche = FicheEchantillon.objects.get(code=slug)
    context ={
        'fiche':fiche,
        'echantillons':fiche.echantillons.all()
    }
    return render(request, 'webpages/echantillonages/details-fiche-echantillonage.html', context)


def ajouter_echantillon(request):
    if request.method == 'POST':
        # 1. Récupération des données du POST
        code = request.POST.get('code')
        fiche_id = request.POST.get('fiche')
        test_id = request.POST.get('test')
        date_prelevement_str = request.POST.get('date_prelevement')
        date_reception_str = request.POST.get('date_reception')
        raison_id = request.POST.get('raison_prelevement')
        fosa_id = request.POST.get('fosa')
        enfant_id = request.POST.get('enfant')
        
        # Checkboxes (renvoient 'on' si cochées, sinon absent du POST)
        is_symptome_present = request.POST.get('is_symptome_present') == 'on'
        is_allaitement_present = request.POST.get('is_allaitement_present') == 'on'
        
        mode_allaitement_id = request.POST.get('mode_allaitement')
        date_sevrage_str = request.POST.get('date_sevrage')
        if_not_sevrage_preciser = request.POST.get('if_not_sevrage_preciser')
        
        is_use_cotrimoxazole = request.POST.get('is_use_cotrimoxazole') == 'on'
        date_cotri_str = request.POST.get('if_use_cotrimoxazole_preciser_date')
        
        is_use_tarv = request.POST.get('is_use_tarv') == 'on'
        date_tarv_str = request.POST.get('if_use_tarv_preciser_date')
        
        if_yes_preciser = request.POST.get('if_yes_preciser')
        
        # PCR Données
        date_pcr1_str = request.POST.get('date_pcr1')
        resultat_pcr1_id = request.POST.get('resultat_pcr1')
        date_pcr2_str = request.POST.get('date_pcr2')
        resultat_pcr2_id = request.POST.get('resultat_pcr2')
        resultat_pcr3_id = request.POST.get('resultat_pcr3')
        again_prelevement = request.POST.get('again_prelevement') == 'on'
        
        # Préleveur & Notes
        nom_preleveur = request.POST.get('nom_preleveur')
        prenom_preleveur = request.POST.get('prenom_preleveur')
        contact_preleveur_id = request.POST.get('contact_preleveur')
        observation = request.POST.get('observation')

        # 2. Nettoyage et conversion des dates / clés étrangères vides
        def parse_date(date_str):
            return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

        try:
            # Récupération des instances requises obligatoires
            fiche = FicheEchantillon.objects.get(id=fiche_id) if fiche_id else None
            test = Test.objects.get(id=test_id) if test_id else None
            contact_preleveur = Personnel.objects.get(id=contact_preleveur_id) if contact_preleveur_id else None

            # Création de l'échantillon
            echantillon = Echantillon.objects.create(
                code=code,
                fiche=fiche,
                test=test,
                date_prelevement=parse_date(date_prelevement_str),
                date_reception=parse_date(date_reception_str),
                observation=observation if observation else None,
                fosa_id=fosa_id if fosa_id else None,
                enfant_id=enfant_id if enfant_id else None,
                is_symptome_present=is_symptome_present,
                is_allaitement_present=is_allaitement_present,
                if_yes_preciser=if_yes_preciser if if_yes_preciser else None,
                date_sevrage=parse_date(date_sevrage_str),
                if_not_sevrage_preciser=if_not_sevrage_preciser if if_not_sevrage_preciser else None,
                is_use_cotrimoxazole=is_use_cotrimoxazole,
                if_use_cotrimoxazole_preciser_date=parse_date(date_cotri_str),
                is_use_tarv=is_use_tarv,
                if_use_tarv_preciser_date=parse_date(date_tarv_str),
                raison_prelevement_id=raison_id if raison_id else None,
                date_pcr1=parse_date(date_pcr1_str),
                date_pcr2=parse_date(date_pcr2_str),
                resultat_pcr1_id=resultat_pcr1_id if resultat_pcr1_id else None,
                resultat_pcr2_id=resultat_pcr2_id if resultat_pcr2_id else None,
                resultat_pcr3_id=resultat_pcr3_id if resultat_pcr3_id else None,
                again_prelevement=again_prelevement,
                nom_preleveur=nom_preleveur if nom_preleveur else None,
                prenom_preleveur=prenom_preleveur if prenom_preleveur else None,
                contact_preleveur=contact_preleveur,
                mode_allaitement_id=mode_allaitement_id if mode_allaitement_id else None,
            )
            
            messages.success(request, f"L'échantillon {echantillon.code} a été enregistré avec succès.")
            return redirect('liste_echantillons') # Mettez ici le nom de votre URL de redirection

        except Exception as e:
            messages.error(request, f"Une erreur est survenue lors de l'enregistrement : {str(e)}")

    # 3. Contexte pour le chargement initial du formulaire (GET)
    context = {
        'fiches_echantillon': FicheEchantillon.objects.all(),
        'tests': Test.objects.all(),
        'raisons_prelevement': RaisonPrelevement.objects.all(),
        'structures': Structure.objects.all(),
        'patients': Patient.objects.all(),
        'modes_allaitement': ModeAllaitement.objects.all(),
        'resultats_pcr': ResultatPcr.objects.all(),
        'personnels': Personnel.objects.all(),
    }
    
    return render(request, 'votre_application/votre_template.html', context)



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