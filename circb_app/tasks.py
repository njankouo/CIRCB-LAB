import os
import base64
from celery import shared_task
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.staticfiles import finders
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from weasyprint import HTML
from datetime import datetime
from .models import Echantillon, Fosa, District, Region, Patient, FicheEchantillon, FosaTransferLog, User
import io
import openpyxl
from django.db import transaction
User = get_user_model()

@shared_task
def generate_pdf_async(echantillon_id, user_id, base_uri):
    resultat = get_object_or_404(Echantillon, id=echantillon_id)
    user = get_object_or_404(User, id=user_id) if user_id else None

    # 1. Chargement du logo
    logo_base64 = ""
    logo_path = finders.find("images/Logo-CIRCB.png") or finders.find("images/logo_circb.png")

    if logo_path and os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Contexte HTML
    context = {
        "resultat": resultat,
        "responsable": user,
        "logo_base64": logo_base64,
        "date_impression": timezone.now(),
    }

    # 3. Rendu du template
    html_content = render_to_string("webpages/rapports/resultat-individuel.html", context)

    # 4. Génération du PDF
    pdf_file = HTML(string=html_content, base_url=base_uri).write_pdf()

    # 5. Stockage du résultat :
    # OPTION A : Sauvegarder le fichier PDF dans un champ FileField du modèle Echantillon
    filename = f"Resultat_{resultat.id}.pdf"
    resultat.fichier_pdf.save(filename, ContentFile(pdf_file), save=True)

    return f"PDF {filename} généré avec succès."



from celery import shared_task
from django.utils.dateparse import parse_date
from .models import Echantillon
def parse_date_custom(date_str):
    """
    Tente de convertir une chaîne de caractères en objet date Django 
    en gérant les formats JJ-MM-AAAA, JJ/MM/AAAA et AAAA-MM-JJ.
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # 1. Essai avec le format français JJ-MM-AAAA ou JJ/MM/AAAA
    for fmt in ('%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
            
    # 2. Fallback sur le parser standard Django (AAAA-MM-JJ)
    return parse_date(date_str)


@shared_task
def bulk_update_echantillons_async(updates_data, global_date_str=None):
    """
    Tâche Celery pour la mise à jour en masse d'échantillons.
    """
    if not updates_data:
        return "Aucune donnée à mettre à jour."

    echantillons_ids = [item['id'] for item in updates_data]

    # Parsing sécurisé de la date globale
    parsed_global_date = parse_date_custom(global_date_str)

    # Récupération des objets en une seule requête SQL
    echantillons_map = {
        ech.id: ech 
        for ech in Echantillon.objects.filter(id__in=echantillons_ids)
    }
    
    updated_objects = []

    for item in updates_data:
        ech_id = item.get('id')
        ech = echantillons_map.get(ech_id)
        
        if ech:
            res_id = str(item.get('resultat_id', '')).strip()
            tests_val = str(item.get('tests', '') or item.get('test_id', '')).strip()
            item_date_str = str(item.get('date_resultat', '')).strip()

            # 1. Clé étrangère ResultatPcr
            ech.resultat_pcr_id = int(res_id) if res_id.isdigit() else None

            # 2. Champ Texte 'tests' (modèle Echantillon)
            if tests_val:
                ech.tests = tests_val

            # 3. Gestion prioritaire de la date
            if item_date_str:
                ech.date_resultat = parse_date_custom(item_date_str)
            elif parsed_global_date:
                ech.date_resultat = parsed_global_date

            updated_objects.append(ech)

    # Exécution de l'UPDATE SQL groupé
    if updated_objects:
        Echantillon.objects.bulk_update(
            updated_objects, 
            ['resultat_pcr_id', 'tests', 'date_resultat']
        )
        return f"{len(updated_objects)} échantillon(s) mis à jour avec succès via Celery."

    return "Aucun échantillon trouvé pour mise à jour."


@shared_task(bind=True)
def task_transfert_fosa(
    self, fosa_id, nouveau_district_id, old_code, new_code, user_id=None
):
  fosa = get_object_or_404(Fosa, pk=fosa_id)
  nouveau_district = get_object_or_404(District, pk=nouveau_district_id)

  ancien_district_nom = str(
      fosa.parent if hasattr(fosa, 'parent') else getattr(fosa, 'district', '')
  )

  fiches_concernees = FicheEchantillon.objects.filter(fosa=fosa)
  patients_concernes = Patient.objects.filter(code__startswith=old_code)

  total_fiches = fiches_concernees.count()
  total_patients = patients_concernes.count()
  total_steps = 1 + total_fiches + total_patients
  current_step = 0
  last_reported_percent = -1

  def update_progress(step_name):
    nonlocal current_step, last_reported_percent
    current_step += 1
    percent = int((current_step / total_steps) * 100) if total_steps > 0 else 100

    # Throttling pour éviter de saturer Redis et de bloquer les requêtes AJAX
    if (
        percent != last_reported_percent
        or current_step == total_steps
        or current_step % 20 == 0
    ):
      last_reported_percent = percent
      self.update_state(
          state='PROGRESS',
          meta={
              'current': current_step,
              'total': total_steps,
              'percent': percent,
              'step_name': step_name,
          },
      )

  # 1. Transfert FOSA
  update_progress('Mise à jour de la structure FOSA')
  if hasattr(fosa, 'parent'):
    fosa.parent = nouveau_district
  elif hasattr(fosa, 'district'):
    fosa.district = nouveau_district
  fosa.save()

  # 2. Fiches échantillons
  for fiche in fiches_concernees:
    if hasattr(fiche, 'district'):
      fiche.district = nouveau_district
    elif hasattr(fiche, 'parent'):
      fiche.parent = nouveau_district
    if hasattr(fiche, 'region'):
      fiche.region = nouveau_district.parent
    fiche.save()
    update_progress('Mise à jour des fiches échantillons')

  # 3. Patients
  for patient in patients_concernes:
    if patient.code and len(patient.code) >= 11:
      suffixe = patient.code[11:]
      patient.code = f'{new_code}{suffixe}'
    elif patient.code:
      patient.code = f'{new_code}'

    if hasattr(patient, 'district'):
      patient.district = nouveau_district
    elif hasattr(patient, 'parent'):
      patient.parent = nouveau_district
    if hasattr(patient, 'region'):
      patient.region = nouveau_district.parent
    patient.save()
    update_progress('Mise à jour des codes patients')

  # 4. Enregistrement dans la table d'historique (FosaTransferLog)
  User = get_user_model()
  user = User.objects.filter(pk=user_id).first() if user_id else None

  FosaTransferLog.objects.create(
      fosa=fosa,
      fosa_nom=fosa.nom,
      ancien_district=ancien_district_nom,
      nouveau_district=nouveau_district.nom,
      old_code=old_code,
      new_code=new_code,
      fiches_mises_a_jour=total_fiches,
      patients_mis_a_jour=total_patients,
      effectue_par=user,
  )

  return {
      'percent': 100,
      'fiches_count': total_fiches,
      'patients_count': total_patients,
  }


@shared_task
def importer_rang_naissance_task(file_bytes):
    """Tâche exécutée en arrière-plan via Redis / Celery."""
    try:
        # Conversion des octets reçus en flux mémoire pour openpyxl
        file_stream = io.BytesIO(file_bytes)
        wb = openpyxl.load_workbook(file_stream, data_only=True)
        sheet = wb.active

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return {"status": "error", "message": "Le fichier Excel est vide."}

        # Détection automatique des colonnes 'id' et 'rang_naissance'
        headers = [
            str(cell).strip().lower() if cell is not None else ""
            for cell in rows[0]
        ]

        if "id" not in headers or "rang_naissance" not in headers:
            return {
                "status": "error",
                "message": "En-têtes manquants dans le fichier. Les colonnes 'id' et 'rang_naissance' sont requises.",
            }

        id_idx = headers.index("id")
        rang_idx = headers.index("rang_naissance")

        success_count = 0
        not_found_count = 0
        invalid_rows = 0

        # Traitement sécurisé sous transaction SQL
        with transaction.atomic():
            for row in rows[1:]:
                raw_id = row[id_idx] if len(row) > id_idx else None
                raw_rang = row[rang_idx] if len(row) > rang_idx else None

                if raw_id is None or raw_rang is None:
                    continue

                try:
                    patient_id = int(raw_id)
                    rang_naissance = int(raw_rang)
                except (ValueError, TypeError):
                    invalid_rows += 1
                    continue

                updated = Patient.objects.filter(id=patient_id).update(
                    rang_naissance=rang_naissance
                )

                if updated:
                    success_count += 1
                else:
                    not_found_count += 1

        msg = f"{success_count} patient(s) mis à jour avec succès."
        if not_found_count > 0:
            msg += f" {not_found_count} ID non trouvé(s)."
        if invalid_rows > 0:
            msg += f" {invalid_rows} ligne(s) ignorée(s) (données invalides)."

        return {"status": "success", "message": msg}

    except Exception as e:
        return {
            "status": "error",
            "message": f"Erreur lors de la lecture du fichier : {str(e)}",
        }