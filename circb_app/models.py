from django.db import models
from django.contrib.auth.models import User

class Personnel(models.Model):
    nom = models.CharField(max_length=128, blank=True, null=True)
    prenom = models.CharField(max_length=128, blank=True, null=True)
    mail = models.EmailField(max_length=128, blank=True, null=True)  # Changé en EmailField pour la validation automatique
    tel = models.CharField(max_length=128, blank=True, null=True)
    photo = models.FileField(blank=True, null=True, upload_to='personnel_photos/')
    sexe = models.CharField(max_length=255, null=True, blank=True)
    bd_user = models.OneToOneField(User, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        if self.nom or self.prenom:
            return f"{self.nom or ''} {self.prenom or ''}".strip()
        return f"Personnel N°{self.id}"


class Test(models.Model):
    code = models.CharField(null=True, max_length=255)
    nom = models.CharField(null=True, max_length=255)

    def __str__(self):
        return f"{self.code} - {self.nom}" if self.code else f"{self.nom}"


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
    receptioniste = models.ForeignKey(User, on_delete=models.CASCADE)
    date_reception = models.DateField(null=True)
    observation = models.TextField(null=True, blank=True)
    
    # Vos clés étrangères uniques vers le modèle Structure
    region = models.ForeignKey(
        Structure, 
        on_delete=models.CASCADE, 
        related_name='fiches_regionales'
    )
    district = models.ForeignKey(
        Structure, 
        on_delete=models.CASCADE, 
        related_name='fiches_districtuales'
    )
    fosa = models.ForeignKey(
        Structure, 
        on_delete=models.CASCADE, 
        related_name='fiches_fosa'
    )
    
    nombre_echantillon = models.IntegerField(null=True)
    date_expedition = models.DateField(null=True)

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
    sexe = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Féminin')], null=True, blank=True)
    contact = models.ForeignKey(Personnel, on_delete=models.SET_NULL, null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    mode_accouchement = models.ForeignKey(ModeAccouchement, on_delete=models.SET_NULL, null=True, blank=True)
    date_prochain_rdv = models.DateField(null=True, blank=True)
    date_diagnostic_lav = models.DateField(null=True, blank=True)
    protocole_ptme = models.ForeignKey(ProtocolePTME, on_delete=models.SET_NULL, null=True, blank=True)
    date_initiation_ptme = models.DateField(null=True, blank=True)
  

    def __str__(self):
        return f"{self.nom} {self.prenom or ''}".strip()
class Patient(models.Model):
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255, null=True, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    sexe = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Féminin')], null=True, blank=True)
    contact = models.ForeignKey(Personnel, on_delete=models.SET_NULL, null=True, blank=True)
    fosa = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients_fosa')
    poids = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Poids en kg
    profilaxie = models.ForeignKey(ProfilaxieArv, on_delete=models.SET_NULL, null=True, blank=True)
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
    code = models.CharField(max_length=255, unique=True)
    fiche = models.ForeignKey(FicheEchantillon, on_delete=models.CASCADE, related_name='echantillons')
    test = models.ForeignKey(Test, on_delete=models.SET_NULL, null=True)
    date_prelevement = models.DateField(null=True)
    date_reception = models.DateField(null=True)
    observation = models.TextField(null=True, blank=True)
    fosa = models.ForeignKey(Structure, on_delete=models.SET_NULL, null=True, related_name='echantillons_fosa')
    enfant =models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, related_name='echantillons_enfant')
    is_symptome_present = models.BooleanField(default=False)
    is_allaitement_present = models.BooleanField(default=False)
    if_yes_preciser = models.TextField(null=True, blank=True)
    date_sevrage = models.DateField(null=True, blank=True)
    if_not_sevrage_preciser = models.TextField(null=True, blank=True)
    is_use_cotrimoxazole = models.BooleanField(default=False)
    if_use_cotrimoxazole_preciser_date = models.DateField(null=True, blank=True)
    is_use_tarv = models.BooleanField(default=False)
    if_use_tarv_preciser_date = models.DateField(null=True, blank=True)
    raison_prelevement = models.ForeignKey(RaisonPrelevement, on_delete=models.SET_NULL, null=True, blank=True)
    date_pcr1 = models.DateField(null=True, blank=True)
    date_pcr2 = models.DateField(null=True, blank=True)
    date_prelevement = models.DateField(null=True, blank=True)
    
    resultat_pcr1 = models.ForeignKey(ResultatPcr, on_delete=models.SET_NULL, null=True, blank=True, related_name='resultats_pcr1')
    resultat_pcr2 = models.ForeignKey(ResultatPcr, on_delete=models.SET_NULL, null=True, blank=True, related_name='resultats_pcr2')
    resultat_pcr3 = models.ForeignKey(ResultatPcr, on_delete=models.SET_NULL, null=True, blank=True, related_name='resultats_final')
    date_prelevement = models.DateField(null=True, blank=True)
    again_prelevement = models.BooleanField(default=False)
    nom_preleveur = models.CharField(max_length=255, null=True, blank=True)
    prenom_preleveur = models.CharField(max_length=255, null=True, blank=True)
    contact_preleveur = models.ForeignKey(Personnel, on_delete=models.SET_NULL, null=True, blank=True, related_name='echantillons_preleveur')
    mode_allaitement = models.ForeignKey(ModeAllaitement, on_delete=models.SET_NULL, null=True, blank=True)
    
    
    
    

    def __str__(self):
        return f"Echantillon {self.code} (Fiche: {self.fiche.code})"