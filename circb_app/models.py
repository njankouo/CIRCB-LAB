from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
class Role(models.Model):
    """Liste des rôles applicatifs disponibles dans l'ERP"""
    code = models.SlugField( help_text="Ex: biologiste, receptioniste, data-manager")
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nom
class RoleUser(models.Model):
    """Association entre un utilisateur et un rôle spécifique."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="users")

    class Meta:
        unique_together = ('user', 'role')  # Assure qu'un utilisateur ne peut pas avoir le même rôle plusieurs fois

    def __str__(self):
        return f"{self.user.username} - {self.role.nom}"


class Transporteur(models.Model):
    code = models.CharField(null=True, max_length=255)
    nom = models.CharField(null=True, max_length=255)
    tel = models.CharField(max_length=32, null=True, blank=True)  # Changé en CharField pour supporter les indicatifs (+237, 00, etc.)
    email = models.EmailField(max_length=255, null=True, blank=True)  # Changé en EmailField

    def __str__(self):
        return f"{self.nom} ({self.code})" if self.code else f"{self.nom}"


class MoyenTransport(models.Model):
    code = models.CharField(null=True, max_length=255)
    nom = models.CharField(null=True, max_length=255)

    def __str__(self):
        return f"{self.nom}"


class Structure_Hierachy(models.Model):
    nom = models.CharField(max_length=255, null=True)
    rang = models.PositiveIntegerField()
    code = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.nom} (Rang {self.rang})"


class Structure(models.Model):
    nom = models.CharField(max_length=255)
    designation = models.CharField(max_length=255, null=True, blank=True)
    date_creation = models.DateTimeField(db_index=True, auto_now_add=True, null=True)
    hierachy = models.ForeignKey(Structure_Hierachy, on_delete=models.SET_NULL, blank=True, null=True, related_name='structures')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    def __str__(self):
        # Affiche le nom, et ajoute le code/désignation entre parenthèses s'il existe
        return f"{self.nom} [{self.designation}]" if self.designation else self.nom
    
    class Meta:
        verbose_name_plural = "Structures"
        ordering = ['nom']  # Tri par nom par défaut
        
        permissions = [
            ("peut_voir_structures", "Peut voir les structures"),
            ("peut_modifier_structures", "Peut modifier les structures"),
            ("peut_supprimer_structures", "Peut supprimer les structures"),
            ("peut_ajouter_structures", "Peut ajouter de nouvelles structures"),
        ]
class StructureBase(models.Model):
    """
    Modèle abstrait pour regrouper les champs communs aux structures 
    (Region, District, Fosa) et éviter la duplication de code.
    """
    nom = models.CharField(max_length=255)
    designation = models.CharField(max_length=255, null=True, blank=True)
    date_creation = models.DateTimeField(db_index=True, auto_now_add=True, null=True)
    # Remplacement du related_name générique par un dynamique via %(class)s
    hierachy = models.ForeignKey(
        'Structure_Hierachy', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='%(class)s_structures'
    )

    def __str__(self):
        return f"{self.nom} [{self.designation}]" if self.designation else self.nom

    class Meta:
        abstract = True
        ordering = ['nom']
        permissions = [
            ("peut_voir_structures", "Peut voir les structures"),
            ("peut_modifier_structures", "Peut modifier les structures"),
            ("peut_supprimer_structures", "Peut supprimer les structures"),
            ("peut_ajouter_structures", "Peut ajouter de nouvelles structures"),
        ]


class Region(StructureBase):
    class Meta(StructureBase.Meta):
        verbose_name = "Région"
        verbose_name_plural = "Régions"
    @property
    def masked_id(self):
        """Masque l'ID en ajoutant un décalage"""
        return self.id + 10000

    @property
    def url_slug(self):
        """Génère un slug à partir du nom"""
        return slugify(self.nom)

    def get_absolute_url(self):
        # Pointe vers la route qui liste les districts de cette région
        return reverse('district', kwargs={'pk': self.masked_id, 'slug': self.url_slug})


class District(StructureBase):
    parent = models.ForeignKey(
        Region, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children'
    )

    class Meta(StructureBase.Meta):
        verbose_name = "District"
        verbose_name_plural = "Districts"


    @property
    def masked_id(self):
        return self.id + 10000

    @property
    def url_slug(self):
        return slugify(self.nom)

    def get_absolute_url(self):
        # Pointe vers la route des FOSA pour ce district
        return reverse('districts', kwargs={'pk': self.masked_id, 'slug': self.url_slug})


  


class Fosa(StructureBase):
    # CORRECTION : 'district' avec un 'd' minuscule a été remplacé par 'District' (majuscule)
    parent = models.ForeignKey(
        District, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children'
    )

    class Meta(StructureBase.Meta):
        verbose_name = "Fosa"
        verbose_name_plural = "Fosas"


class FicheEchantillon(models.Model):
    code = models.SlugField(unique=True, null=True)
    transporteur = models.TextField(null=True)
    moyen_transport = models.ForeignKey('MoyenTransport', null=True, blank=True, on_delete=models.CASCADE)
    receptioniste = models.CharField(null=True, max_length=255)
    date_reception = models.DateField(null=True)
    observation = models.TextField(null=True, blank=True)
    date_Envoie_labo = models.DateField(null=True)
    expediteur = models.CharField(null=True, max_length=255)
    status = models.BooleanField(default=True, null=True)
    
    # Champs physiques en base de données
    region = models.ForeignKey(
        Region, 
        on_delete=models.CASCADE, 
        related_name='fiches_regionales', 
        null=True, 
        blank=True
    )
    district = models.ForeignKey(
        District, 
        on_delete=models.CASCADE, 
        related_name='fiches_districtuales', 
        null=True, 
        blank=True
    )
    fosa = models.ForeignKey(
        Fosa, 
        on_delete=models.CASCADE, 
        related_name='fiches_fosa', 
        null=True, 
        blank=True
    )

    nombre_echantillon = models.IntegerField(null=True)
    date_expedition = models.DateField(null=True)
    numero_ordre = models.IntegerField(null=True)
    date_enregistrement = models.DateField(null=True)

    def __str__(self):
        return f"Fiche {self.code} ({self.fosa.nom if self.fosa else 'Inconnue'})"
    
    class Meta:
        permissions = [
            ("peut_voir_fiches_expedition", "Peut voir les fiches d'expédition"),
            ("peut_supprimer_fiches_expedition", "Peut supprimer les fiches d'expédition"),
            ("peut_saisir_fiche_expedition", "Peut enregistrer une nouvelle fiche d'expédition"),
            ("peut_modifier_fiches_expedition", "Peut modifier les fiches d'expédition"),
        ]

class PorteEntree(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nom if self.nom else "Porte d'entrée Inconnue"
class ProfilaxieArv(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nom if self.nom else "Profilaxie ARV Inconnue"

class ModeAllaitement(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)
    is_artificiel = models.BooleanField(default=False)  # Nouveau champ pour indiquer si c'est artificiel

    def __str__(self):
        return self.nom if self.nom else "Mode d'allaitement Inconnu"   
class ModeAccouchement(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nom if self.nom else "Mode d'accouchement Inconnu"

class ProtocolePTME(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nom if self.nom else "Protocole PTME Inconnu"
class Mere(models.Model):
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255, null=True, blank=True)
    date_naissance = models.DateField(null=True, blank=True)

    contact = models.CharField(max_length=50, null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)


    def __str__(self):
        return f"{self.nom} {self.prenom or ''}".strip()
class Patient(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    prenom = models.CharField(max_length=255, null=True, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    sexe = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Féminin')], null=True, blank=True)
    mere = models.ForeignKey(Mere, on_delete=models.SET_NULL, null=True, blank=True, related_name='enfants')
   
    fosa = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients_fosa')
     
    # db_index=True direct sur la SlugField
    code = models.SlugField(null=True, blank=True)
    
    porte_entree = models.ForeignKey(PorteEntree, on_delete=models.SET_NULL, null=True, blank=True)
    rang_naissance = models.IntegerField(null=True)
   
    class Meta:
        indexes = [
            models.Index(fields=['nom']),
            models.Index(fields=['prenom']),
            models.Index(fields=['code']),
            # Index composé recommandé si la recherche se fait souvent sur nom + prénom combinés
            models.Index(fields=['nom', 'prenom']),
        ]
        permissions = [
            ("Consulter_dossier_patient", "Consulter le dossier patient"),
            ("modifier_informations_patients", "Modifier les informations des patients"),
                 
        ]   

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.code})"
    
  

class RaisonPrelevement(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nom if self.nom else "Raison de prélèvement Inconnue"

class ResultatPcr(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)
    observation = models.TextField(null=True)

    def __str__(self):
        return self.nom if self.nom else "Résultat PCR Inconnu"
class FichePatient(models.Model):
   
    fiche = models.ForeignKey(FicheEchantillon, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="patients")
    
 
    
    class Meta:
        unique_together = ('fiche', 'patient')


class Echantillon(models.Model):
    
    #enfant Informations
    slug = models.SlugField()
    code = models.IntegerField(null=True, blank=True)
    fiche = models.ForeignKey(FicheEchantillon, on_delete=models.CASCADE, related_name='echantillons')
    
    enfant =models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, related_name='echantillons_enfant')
    poids = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Poids en kg
    profilaxie_arv = models.CharField(max_length=255)
    date_initiation_profilaxie_arv = models.DateField(null=True, blank=True)
    rang_naissance = models.IntegerField(null=True)
    ordre = models.PositiveIntegerField(editable=False, blank=True, null=True)
    
    autre_profilaxie_arv = models.CharField(max_length=255, null=True)
    
    code_ech = models.CharField(max_length=255, null=True, blank=True)
    
    protocole_ptme_autre = models.CharField(max_length=255, null=True)
    
    
    
    #parents Informations
    mere = models.ForeignKey(Mere, on_delete=models.SET_NULL, null=True, blank=True, related_name='echantillons_mere')
    protocole_ptme = models.CharField(max_length=255, null=True, blank=True)
    date_rdv = models.DateField(null=True, blank=True)
    date_diagnostic_lav = models.DateField(null=True, blank=True)
    mode_accouchement = models.IntegerField(null=True, blank=True)
    date_initiation_ptme = models.DateField(null=True, blank=True)
    date_diagnostic_vih = models.DateField(null=True, blank=True)
    numero_grossesse = models.IntegerField(null=True, blank=True)
    nb_enfant_expose = models.IntegerField(null=True, blank=True)
    nb_enfant_infecte = models.IntegerField(null=True, blank=True)
    
    date_initiation_tarv = models.DateField(null=True, blank=True)

    protocole_ptme_mere = models.CharField(max_length=255, null=True, blank=True)
    
  
    
    # Informations sur l'échantillon
    present_symptome = models.IntegerField(null=True, blank=True)
    present_allaitement = models.IntegerField(null=True, blank=True)
    mode_allaitement = models.IntegerField(null=True, blank=True)
    present_sevrage = models.IntegerField(null=True, blank=True)
    date_sevrage = models.DateField(null=True, blank=True)
    present_cotrimoxazole = models.BooleanField(default=False)
    date_cotrimoxazole = models.DateField(null=True, blank=True)
    present_tarv = models.BooleanField(default=False)
    date_tarv = models.DateField(null=True, blank=True)
    code_circb = models.CharField(max_length=255, null=True, blank=True)
    protocol_arv_mere = models.CharField(max_length=255, null=True, blank=True)
  

    raison_prelevement = models.ForeignKey(RaisonPrelevement, on_delete=models.SET_NULL, null=True, blank=True)
    porte_entree = models.ForeignKey(PorteEntree, on_delete=models.SET_NULL, null=True, blank=True)
    
    date_enregistrement = models.DateField(null=True)
    
    protocol_arv_mere = models.CharField(max_length=255, null=True, blank=True)
    
    date_debut_arv = models.DateField(null=True, blank=True)
    
    date_resultat = models.DateField(null=True, blank=True)
    
    date_saisie = models.DateField(null=True, blank=True)
    
    
    
    #INformation sur lechantillon
    
    date_prelevement = models.DateField(null=True, blank=True)
    duplicate_prelevement =models.CharField(null=True, blank=True, max_length=255)
    nom_preleveur = models.CharField(max_length=255)
    prenom_preleveur = models.CharField(max_length=255)
    contact_preleveur = models.IntegerField(null=True)
    observation = models.TextField()
    
    
    examen = models.CharField(max_length=255, null=True, blank=True)
    tests = models.CharField(max_length=255, null=True, blank=True)
    resultat_pcr = models.ForeignKey(
        'ResultatPcr',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='echantillons',
    )
    # Configuration des index
    class Meta:
        indexes = [
            # Index simples sur les dates pour les statistiques / filtres chronologiques
            models.Index(
                fields=["date_prelevement"], name="idx_ech_date_prelev"
            ),
            models.Index(
                fields=["date_enregistrement"], name="idx_ech_date_enregistr"
            ),
            # Index composés pour optimiser l'historique par patient
            models.Index(
                fields=["enfant", "date_prelevement"],
                name="idx_ech_enfant_date",
            ),
            models.Index(
                fields=["fiche", "date_prelevement"], name="idx_ech_fiche_date"
            ),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Récupère la date et l'heure actuelle au format AAAAMMJJ-HHMM
            timestamp = timezone.now().strftime("%Y%m%d-%H%M")
            # Donne un slug du style : "ech-20260710-1032"
            self.slug = slugify(f"ech-{timestamp}")
        if not self.pk: # Si c'est un nouvel échantillon en cours de création
            if self.enfant:
                # Compte uniquement les échantillons appartenant à CET enfant précis
                dernier_ordre = Echantillon.objects.filter(enfant=self.enfant).count()
                self.ordre = dernier_ordre + 1
            else:
                self.ordre = 1
        
        super().save(*args, **kwargs)
    def __str__(self):
        return f"Echantillon {self.slug} (Fiche: {self.fiche.code})"
    
    class Meta:
        permissions = [
            ("peut_voir_consulter_echantillons", "Peut consulter liste des echantillons"),
            ("peut_modifier_echantillons", "Peut Modifier les echantillons"),
            ("peut_saisir_echantillon", "Peut enregistrer un nouvel échantillon"),
            ("peut_supprimer_echantillons", "Peut supprimer les echantillons"),
            ("peut_voir_tableau_de_bord_echantillons", "Peut voir le tableau de bord des echantillons"),
        ]



class Test(models.Model):
    """Configuration/Kit technique ou protocole utilisé."""
    code = models.CharField(max_length=255, null=True, blank=True)
    nom = models.CharField(max_length=255, null=True, blank=True)
    
    

    class Meta:
        verbose_name = "Configuration de Test"
        verbose_name_plural = "Configurations de Tests"

    def __str__(self):
        return f"{self.nom} ({self.nom if self.pk else 'Sans type'})"






class Resultat(models.Model):
    """
    Fiche de validation finale d'un dossier d'analyse.
    Le résultat est directement lié à un verdict de la table ResultatPcr.
    """
    echantillon = models.ForeignKey('Echantillon', on_delete=models.CASCADE, null=True, related_name="resultats")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True, related_name="resultats")
    
    # Liaison avec la table Lexique que tu as demandée
    resultat_pcr = models.ForeignKey(ResultatPcr, on_delete=models.PROTECT, null=True, related_name="resultats_associes")
    
    date_resultat = models.DateField()
    commentaire = models.TextField(blank=True, null=True)
    responsable = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resultats_valides")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    

    class Meta:
        verbose_name = "Résultat d'Analyse"
        verbose_name_plural = "Résultats d'Analyses"
        ordering = ['-date_resultat']
        permissions = [
            ("Consulter_resultat_patient", "Consulter le resultat patient"),
            ("modifier_resultats_patients", "Modifier les resultats des patients"),
            ("supprimer_resultats_patients", "Supprimer les resultats des patients"),
            
                        
         ]
        

    def __str__(self):
        verdict = self.resultat_pcr.nom if self.resultat_pcr else "En attente"
        return f"Échantillon {self.echantillon} -> Verdict : {verdict}"
 
           

class ParametresGlobal(models.Model):
    # Modèle fictif ou technique pour stocker les permissions globales
    class Meta:
        permissions = [
            ("can_export_pdf", "Peut exporter les rapports PDF"),
            ("access_eid_dashboard", "Peut accéder au tableau de bord EID"),
          
            ("manage_user_roles", "Peut gérer les rôles des utilisateurs"),
            ("manage_system_settings", "Peut gérer les paramètres du système"),
            ("manage_rh", "Peut gérer les ressources humaines"),
            ("view_audit_logs", "Peut voir les journaux d'audit"),
        ]


class FosaTransferLog(models.Model):
  # Structure concernée (ForeignKey optionnelle si la FOSA venait à être supprimée plus tard)
  fosa = models.ForeignKey(
      'Fosa',
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='transfer_logs',
      verbose_name='Structure FOSA',
  )

  # Données textuelles figées au moment du transfert (pour l'historique)
  fosa_nom = models.CharField(
      max_length=255, verbose_name='Nom de la FOSA au moment du transfert'
  )
  ancien_district = models.CharField(
      max_length=255, verbose_name='Ancien District'
  )
  nouveau_district = models.CharField(
      max_length=255, verbose_name='Nouveau District'
  )

  # Codes de mise à jour des patients
  old_code = models.CharField(
      max_length=50, blank=True, null=True, verbose_name='Ancien Code'
  )
  new_code = models.CharField(
      max_length=50, blank=True, null=True, verbose_name='Nouveau Code'
  )

  # Volumes traités
  fiches_mises_a_jour = models.IntegerField(
      default=0, verbose_name='Fiches échantillons modifiées'
  )
  patients_mis_a_jour = models.IntegerField(
      default=0, verbose_name='Patients mis à jour'
  )

  # Traçabilité utilisateur et horodatage
  effectue_par = models.ForeignKey(
      User,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      verbose_name='Effectué par',
  )
  date_transfert = models.DateTimeField(
      auto_now_add=True, verbose_name='Date du transfert'
  )

  class Meta:
    verbose_name = 'Historique de transfert FOSA'
    verbose_name_plural = 'Historiques de transferts FOSA'
    ordering = ['-date_transfert']

  def __str__(self):
    return f'Transfert {self.fosa_nom} : {self.ancien_district} -> {self.nouveau_district} ({self.date_transfert.strftime("%d/%m/%Y %H:%M")})'


class TestSerologique(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True)
    resultat = models.CharField(null=True)
    ordre = models.PositiveIntegerField(null=True)
    date_resultat = models.DateField(null=True)