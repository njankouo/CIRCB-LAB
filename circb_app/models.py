from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
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
class Personnel(models.Model):
    roles = models.ManyToManyField(Role, blank=True, related_name="utilisateurs")
    nom = models.CharField(max_length=128, blank=True, null=True)
    prenom = models.CharField(max_length=128, blank=True, null=True)
    mail = models.EmailField(max_length=128, blank=True, null=True)  # Changé en EmailField pour la validation automatique
    tel = models.CharField(max_length=128, blank=True, null=True)
    photo = models.FileField(blank=True, null=True, upload_to='personnel_photos/')
    sexe = models.CharField(max_length=255, null=True, blank=True)
    bd_user = models.OneToOneField(User, blank=True, null=True, on_delete=models.SET_NULL)
    service = models.CharField(max_length=255, null=True)

    def __str__(self):
        if self.nom or self.prenom:
            return f"{self.nom or ''} {self.prenom or ''}".strip()
        return f"Personnel N°{self.id}"



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
    date_creation = models.DateTimeField(db_index=True, auto_now_add=True)
    hierachy = models.ForeignKey(Structure_Hierachy, on_delete=models.SET_NULL, blank=True, null=True, related_name='structures')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    def __str__(self):
        # Affiche le nom, et ajoute le code/désignation entre parenthèses s'il existe
        return f"{self.nom} [{self.designation}]" if self.designation else self.nom


class FicheEchantillon(models.Model):
    code = models.SlugField(unique=True)
    transporteur = models.ForeignKey(Transporteur, null=True, blank=True, on_delete=models.CASCADE)
    moyen_transport = models.ForeignKey(MoyenTransport, null=True, blank=True, on_delete=models.CASCADE)
    receptioniste = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    date_reception = models.DateField(null=True)
    observation = models.TextField(null=True, blank=True)
    
    # Vos clés étrangères uniques vers le modèle Structure
    region = models.ForeignKey(
        Structure, 
        on_delete=models.CASCADE, 
        related_name='fiches_regionales', null=True
    )
    district = models.ForeignKey(
        Structure, 
        on_delete=models.CASCADE, 
        related_name='fiches_districtuales', null=True
    )
    fosa = models.ForeignKey(
        Structure, 
        on_delete=models.CASCADE, 
        related_name='fiches_fosa', null=True
    )
    
    nombre_echantillon = models.IntegerField(null=True)
    date_expedition = models.DateField(null=True)
    numero_ordre = models.IntegerField(null=True)
    date_enregistrement = models.DateField(null=True)
    
    

    def __str__(self):
        return f"Fiche {self.code} ({self.fosa.nom if self.fosa else 'Inconnue'})"

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
    #sexe = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Féminin')], null=True, blank=True)
    contact = models.ForeignKey(Personnel, on_delete=models.SET_NULL, null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
   # mode_accouchement = models.ForeignKey(ModeAccouchement, on_delete=models.SET_NULL, null=True, blank=True)
   # date_prochain_rdv = models.DateField(null=True, blank=True)
   # date_diagnostic_lav = models.DateField(null=True, blank=True)
   # protocole_ptme = models.ForeignKey(ProtocolePTME, on_delete=models.SET_NULL, null=True, blank=True)
   # date_initiation_ptme = models.DateField(null=True, blank=True)
  

    def __str__(self):
        return f"{self.nom} {self.prenom or ''}".strip()
class Patient(models.Model):
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255, null=True, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    sexe = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Féminin')], null=True, blank=True)
    #contact = models.ForeignKey(Personnel, on_delete=models.SET_NULL, null=True, blank=True)
    fosa = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients_fosa')
    poids = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Poids en kg
   # profilaxie = models.ForeignKey(ProfilaxieArv, on_delete=models.SET_NULL, null=True, blank=True)
    mere = models.ForeignKey(Mere, on_delete=models.SET_NULL, null=True, blank=True, related_name='enfants')
    code = models.SlugField(unique=True, null=True, blank=True)  # Code unique pour chaque patient
    porte_entree = models.ForeignKey(PorteEntree, on_delete=models.SET_NULL, null=True, blank=True)
    

    def __str__(self):
        return f"{self.nom} {self.prenom or ''}".strip()

class RaisonPrelevement(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nom if self.nom else "Raison de prélèvement Inconnue"

class ResultatPcr(models.Model):
    nom = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nom if self.nom else "Résultat PCR Inconnu"
class Echantillon(models.Model):
    
    #enfant Informations
    slug = models.SlugField()
    fiche = models.ForeignKey(FicheEchantillon, on_delete=models.CASCADE, related_name='echantillons')
    enfant =models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, related_name='echantillons_enfant')
    poids = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Poids en kg
    profilaxie_arv = models.ForeignKey(ProfilaxieArv, on_delete=models.SET_NULL, null=True, blank=True)
    rang_naissance = models.IntegerField(null=True)
    
    
    #parents Informations
    mere = models.ForeignKey(Mere, on_delete=models.SET_NULL, null=True, blank=True, related_name='echantillons_mere')
    protocole_ptme = models.ForeignKey(ProtocolePTME, on_delete=models.SET_NULL, null=True, blank=True)
    date_rdv = models.DateField(null=True, blank=True)
    date_diagnostic_lav = models.DateField(null=True, blank=True)
    mode_accouchement = models.ForeignKey(ModeAccouchement, on_delete=models.SET_NULL, null=True, blank=True)
    date_initiation_ptme = models.DateField(null=True, blank=True)
    date_diagnostic_vih = models.DateField(null=True, blank=True)
    numero_grossesse = models.IntegerField(null=True, blank=True)
    nb_enfant_expose = models.IntegerField(null=True, blank=True)
    nb_enfant_infecte = models.IntegerField(null=True, blank=True)
    
    
    # Informations sur l'échantillon
    present_symptome = models.BooleanField(default=False)
    present_allaitement = models.BooleanField(default=False)
    mode_allaitement = models.ForeignKey(ModeAllaitement, on_delete=models.SET_NULL, null=True, blank=True)
    present_sevrage = models.BooleanField(default=False)
    date_sevrage = models.DateField(null=True, blank=True)
    present_cotrimoxazole = models.BooleanField(default=False)
    date_cotrimoxazole = models.DateField(null=True, blank=True)
    present_tarv = models.BooleanField(default=False)
    date_tarv = models.DateField(null=True, blank=True)
    pcr_1=models.BooleanField(default=False)
    pcr_2 = models.BooleanField(default=False)
    autre_pcr = models.BooleanField(default=False)
    resultat_pcr = models.ForeignKey(ResultatPcr, on_delete=models.SET_NULL, null=True, blank=True)
    raison_prelevement = models.ForeignKey(RaisonPrelevement, on_delete=models.SET_NULL, null=True, blank=True)
    porte_entree = models.ForeignKey(PorteEntree, on_delete=models.SET_NULL, null=True, blank=True)
    
    
    #INformation sur lechantillon
    
    date_prelevement = models.DateField()
    duplicate_prelevement =models.BooleanField(default=False)
    nom_preleveur = models.CharField(max_length=255)
    prenom_preleveur = models.CharField(max_length=255)
    contact_preleveur = models.IntegerField()
    observation = models.TextField()
    
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Récupère la date et l'heure actuelle au format AAAAMMJJ-HHMM
            timestamp = timezone.now().strftime("%Y%m%d-%H%M")
            # Donne un slug du style : "ech-20260710-1032"
            self.slug = slugify(f"ech-{timestamp}")
        super().save(*args, **kwargs)
    def __str__(self):
        return f"Echantillon {self.slug} (Fiche: {self.fiche.code})"



class Pcr(models.Model):
    """Classification de la PCR (ex: PCR-1, PCR-2, Charge Virale)."""
    code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    nom = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Type de PCR"
        verbose_name_plural = "Types de PCR"

    def __str__(self):
        return f"[{self.code}] {self.nom}" if self.code else self.nom


class Test(models.Model):
    """Configuration/Kit technique ou protocole utilisé."""
    code = models.CharField(max_length=255, null=True, blank=True)
    nom = models.CharField(max_length=255, null=True, blank=True)
    pcr = models.ForeignKey(Pcr, on_delete=models.CASCADE, null=True, blank=True, related_name="tests")

    class Meta:
        verbose_name = "Configuration de Test"
        verbose_name_plural = "Configurations de Tests"

    def __str__(self):
        return f"{self.nom} ({self.pcr.nom if self.pcr else 'Sans type'})"






class Resultat(models.Model):
    """
    Fiche de validation finale d'un dossier d'analyse.
    Le résultat est directement lié à un verdict de la table ResultatPcr.
    """
    echantillon = models.ForeignKey('Echantillon', on_delete=models.CASCADE, null=True, related_name="resultats")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True, related_name="resultats")
    
    # Liaison avec la table Lexique que tu as demandée
    resultat_pcr = models.ForeignKey(ResultatPcr, on_delete=models.PROTECT, null=True, related_name="resultats_associes")
    
    date_prelevement = models.DateField()
    commentaire = models.TextField(blank=True, null=True)
    responsable = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resultats_valides")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Résultat d'Analyse"
        verbose_name_plural = "Résultats d'Analyses"
        ordering = ['-date_prelevement']

    def __str__(self):
        verdict = self.resultat_pcr.nom if self.resultat_pcr else "En attente"
        return f"Échantillon {self.echantillon} -> Verdict : {verdict}"
