from django.shortcuts import render

# Create your views here.
def connexion_view(request):
    # Django ira chercher ce fichier dans vos dossiers de templates configurés
    return render(request, 'webpages/login_hosp.html')


def dashboard(request):
    return render(request, 'webpages/dashbord_hosp.html')

def personnel(request):
    return render(request, 'webpages/personnel.html')