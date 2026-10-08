$ErrorActionPreference = "Stop"

# Configuration des variables
$dossier   = "C:\circb_projet\nginx\ssl\prod"
$cert      = "$dossier\medisys+5.pem"
$key       = "$dossier\medisys+5-key.pem"
$domaines  = "medisys-eid", "localhost", "127.0.0.1"
$conteneur = "circb_nginx"
$logDir    = "C:\Scripts"
$log       = "$logDir\renouveler-ssl.log"

# Assure que le dossier de logs existe
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Start-Transcript -Path $log -Append

try {
    # 1. Sauvegarde de la configuration précédente
    Copy-Item $cert "$cert.bak" -Force -ErrorAction SilentlyContinue
    Copy-Item $key "$key.bak" -Force -ErrorAction SilentlyContinue

    # 2. Régénération avec mkcert
    mkcert -cert-file $cert -key-file $key $domaines
    if ($LASTEXITCODE -ne 0) { throw "mkcert a échoué avec le code $LASTEXITCODE" }

    # 3. Validation de la configuration Nginx dans Docker
    docker exec $conteneur nginx -t
    if ($LASTEXITCODE -ne 0) { throw "Configuration Nginx invalide dans le conteneur" }

    # 4. Rechargement de Nginx sans interruption
    docker exec $conteneur nginx -s reload
    if ($LASTEXITCODE -ne 0) { throw "Rechargement Nginx échoué" }

    Write-Host "Renouvellement réussi : $(Get-Date)"
}
catch {
    Write-Host "ERREUR : $_"
    
    # Restauration des anciens certificats
    Copy-Item "$cert.bak" $cert -Force -ErrorAction SilentlyContinue
    Copy-Item "$key.bak" $key -Force -ErrorAction SilentlyContinue
    exit 1
}
finally {
    Stop-Transcript
}
