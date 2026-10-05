import os
from celery import Celery

# Définir le module de réglages Django par défaut pour 'celery'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'circb_projet.settings')

app = Celery('circb_projet')

# Charger les configurations depuis settings.py en utilisant le préfixe CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Charger automatiquement les tâches (tasks.py) de toutes les applications Django installées
app.autodiscover_tasks()