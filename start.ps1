# ══════════════════════════════════════════════════════════════
# PFE Data Platform — Script de démarrage complet (Windows)
# Séquence : Build → Services → Init Bronze → Seed OLTP → Airflow
# ══════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot
$COMPOSE = "docker compose -f $ROOT\docker\docker-compose.yml --env-file $ROOT\.env"

function Log($msg) { Write-Host "`n[START] $msg" -ForegroundColor Cyan }
function Ok($msg)  { Write-Host "  OK  $msg" -ForegroundColor Green }
function Warn($msg){ Write-Host "  !!  $msg" -ForegroundColor Yellow }

# ─── 0. Vérifications préalables ──────────────────────────────
Log "Vérification des prérequis..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker n'est pas installé ou n'est pas dans le PATH." -ForegroundColor Red; exit 1
}
if (-not (Test-Path "$ROOT\.env")) {
    Write-Host "Fichier .env introuvable à la racine du projet." -ForegroundColor Red; exit 1
}

# Créer les répertoires nécessaires au pipeline
New-Item -ItemType Directory -Force -Path "$ROOT\data\processed" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\data\processed\dq_reports" | Out-Null
New-Item -ItemType Directory -Force -Path "$ROOT\airflow\logs" | Out-Null
Ok "Répertoires créés."

# ─── 1. Build des images Docker ───────────────────────────────
Log "Build des images Docker (Airflow, FastAPI, dbt-docs)..."
Invoke-Expression "$COMPOSE build --no-cache"
Ok "Images construites."

# ─── 2. Démarrage des bases de données ────────────────────────
Log "Démarrage de postgres_source, postgres_dwh, postgres_infra..."
Invoke-Expression "$COMPOSE up -d postgres_source postgres_dwh postgres_infra"

Log "Attente que les bases de données soient healthy (60s max)..."
$timeout = 60
$elapsed = 0
while ($elapsed -lt $timeout) {
    $healthy = docker compose -f "$ROOT\docker\docker-compose.yml" ps --format json 2>$null |
               ConvertFrom-Json |
               Where-Object { $_.Name -match "postgres_(source|dwh|infra)" -and $_.Health -eq "healthy" }
    if (($healthy | Measure-Object).Count -eq 3) { break }
    Start-Sleep -Seconds 5
    $elapsed += 5
    Write-Host "  ... $elapsed`s" -NoNewline
}
Ok "Bases de données prêtes."

# ─── 3. Seed OLTP (postgres_source) ──────────────────────────
Log "Chargement des données sources dans postgres_source..."
Warn "Cette étape charge ~550K lignes — peut prendre 1-2 minutes."

$seedFiles = @(
    "$ROOT\data\raw\postgres_source\customers.csv",
    "$ROOT\data\raw\postgres_source\orders.csv",
    "$ROOT\data\raw\postgres_source\order_items.csv",
    "$ROOT\data\raw\postgres_source\order_payments.csv",
    "$ROOT\data\raw\postgres_source\order_reviews.csv"
)
$missing = $seedFiles | Where-Object { -not (Test-Path $_) }
if ($missing) {
    Warn "Fichiers CSV manquants : $missing — seed OLTP ignoré."
} else {
    # Lancer seed_oltp via un container temporaire (réutilise l'image airflow déjà buildée)
    docker run --rm `
        --network pfe-data-platform_default `
        -e POSTGRES_SOURCE_HOST=postgres_source `
        -e POSTGRES_SOURCE_PORT=5432 `
        -e POSTGRES_SOURCE_USER=admin `
        -e POSTGRES_SOURCE_PASSWORD=admin `
        -e POSTGRES_SOURCE_DB=oltp_db `
        -v "${ROOT}:/opt/airflow" `
        -w /opt/airflow `
        pfe-data-platform-airflow-webserver `
        python src/scripts/seed_oltp.py
    Ok "OLTP seedé."
}

# ─── 4. Démarrage complet (airflow-init inclus) ───────────────
Log "Démarrage de tous les services (airflow-init initialise le schéma Bronze)..."
Invoke-Expression "$COMPOSE up -d"

Log "Attente de airflow-init (initialise Airflow DB + schéma Bronze)..."
$timeout = 180
$elapsed = 0
while ($elapsed -lt $timeout) {
    $state = docker inspect airflow_init --format "{{.State.Status}}" 2>$null
    if ($state -eq "exited") { break }
    Start-Sleep -Seconds 5
    $elapsed += 5
    Write-Host "  ... $elapsed`s" -NoNewline
}
$exitCode = docker inspect airflow_init --format "{{.State.ExitCode}}" 2>$null
if ($exitCode -ne "0") {
    Warn "airflow-init s'est terminé avec le code $exitCode — vérifier les logs : docker logs airflow_init"
} else {
    Ok "airflow-init terminé. Schéma Bronze initialisé."
}

# ─── 5. Résumé des services ───────────────────────────────────
Log "Services disponibles :"
Write-Host ""
Write-Host "  ALTEN React UI    http://localhost:3001" -ForegroundColor Cyan
Write-Host "  Airflow UI        http://localhost:8080    (admin/admin)" -ForegroundColor White
Write-Host "  FastAPI (mock)    http://localhost:8090/docs" -ForegroundColor White
Write-Host "  dbt Lineage       http://localhost:8085" -ForegroundColor White
Write-Host "  Grafana           http://localhost:3000    (admin/admin)" -ForegroundColor White
Write-Host "  pgAdmin           http://localhost:5050    (admin@admin.com/admin)" -ForegroundColor White
Write-Host "  Prometheus        http://localhost:9090" -ForegroundColor White
Write-Host ""

# ─── 6. Lancement du DAG principal ───────────────────────────
Log "Pour lancer le pipeline manuellement depuis Airflow CLI :"
Write-Host "  docker exec airflow_scheduler airflow dags trigger e-commerce_platform_industrialized" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ou activer le DAG dans l'UI Airflow : http://localhost:8080" -ForegroundColor Yellow
Write-Host ""
Ok "Plateforme démarrée. Bon PFE !"
