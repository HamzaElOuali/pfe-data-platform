# Olist Data Platform — PFE Data Engineering

Plateforme de données End-to-End construite à partir du dataset **Olist** (e-commerce brésilien).  
Couvre l'ensemble de la chaîne de valeur data : **ingestion multi-sources → stockage lakehouse → transformation → exposition analytique**.

> **Phase A** — On-Premises · Architecture ELT · Docker Compose

---

## Architecture

```
Sources (3)            Ingestion              Storage & Processing         Serving
┌──────────┐     ┌─────────────────┐     ┌───────────────────────────┐    ┌────────────┐
│ CSV       │────▶│ Beam Pipeline 1 │────▶│ MinIO Bronze (Parquet)    │    │ Power BI   │
│ (Legacy)  │     │ Full Refresh    │     │          │                │    │ DuckDB SQL │
├──────────┤     ├─────────────────┤     │    DuckDB + dbt-core      │───▶│ ML Models  │
│ PostgreSQL│────▶│ Beam Pipeline 2 │────▶│    Silver (Clean)         │    │ dbt docs   │
│ (OLTP)    │     │ Incr. Watermark │     │    Gold (SSOT / KPIs)     │    └────────────┘
├──────────┤     ├─────────────────┤     └───────────────────────────┘
│ FastAPI   │────▶│ Beam Pipeline 3 │          ▲ Orchestration: Airflow
│ (REST)    │     │ Full Refresh    │          ▲ Qualité: GE + dbt tests
└──────────┘     └─────────────────┘          ▲ Monitoring: Prometheus/Grafana
```

## Stack Technologique

| Couche | Technologie | Version | Rôle |
|---|---|---|---|
| Ingestion | Apache Beam (DirectRunner) | 2.54.0 | 3 pipelines batch (CSV, JDBC, REST) |
| Stockage | MinIO | latest | Object Store S3-compatible (Bronze) |
| Processing | DuckDB | 0.10.3 | Moteur SQL analytique local |
| Transformation | dbt-core + dbt-duckdb | 1.7.x | ELT Bronze → Silver → Gold |
| Orchestration | Apache Airflow | 2.9.1 | DAGs, scheduling, retry |
| Data Quality | Great Expectations + dbt tests | 0.18.19 | Validation entrée + intégrité |
| Monitoring | Prometheus + Grafana | latest | Observabilité infra & data |
| API Mock | FastAPI | 0.111.0 | Simule catalogue produits & vendeurs |
| Catalogue | dbt docs | — | Lineage, documentation modèles |
| Conteneurisation | Docker Compose | v2 | Plateforme autonome Phase A |

## Structure du Projet

```
pfe-data-platform/
├── src/                      ← Code Python source
│   ├── ingestion/            ← Pipelines Apache Beam
│   ├── processing/           ← Transformations, nettoyage
│   └── utils/                ← Fonctions utilitaires partagées
├── airflow/                  ← Orchestration Airflow
│   ├── dags/                 ← DAGs Airflow
│   ├── plugins/              ← Plugins customisés
│   └── logs/                 ← Logs d'exécution (gitignored)
├── dbt/                      ← Modèles dbt (Bronze / Silver / Gold)
│   ├── models/
│   ├── macros/
│   ├── seeds/
│   ├── profiles.yml
│   └── dbt_project.yml
├── data/
│   ├── raw/                  ← Données brutes (lecture seule, gitignored)
│   └── processed/            ← Données transformées (gitignored)
├── api/                      ← API mock FastAPI (products, sellers)
│   └── main.py
├── docker/
│   ├── docker-compose.yml    ← Orchestration des services
│   ├── Dockerfile
│   ├── Dockerfile.dbt
│   └── monitoring/           ← Prometheus + Grafana config
├── notebooks/                ← Exploration / prototypage
├── tests/                    ← Tests pytest
├── docs/                     ← Documentation technique
├── Dockerfile                ← Image Airflow + dépendances Data
├── requirements.txt          ← Dépendances Python (production)
├── requirements-dev.txt      ← Dépendances Python (dev)
├── .env.example              ← Template variables d'environnement
├── .gitignore
├── .dockerignore
└── .python-version           ← Python 3.11
```

## Getting Started

### Prérequis

- **Python 3.11+**
- **Docker Desktop 24+** avec Docker Compose v2
- **Git**

### 1. Cloner le dépôt

```bash
git clone https://github.com/<org>/pfe-data-platform.git
cd pfe-data-platform
```

### 2. Configurer l'environnement Python

```bash
# Créer un environnement virtuel
python -m venv .venv

# Activer l'environnement
# Windows PowerShell :
.venv\Scripts\Activate.ps1
# Linux / macOS :
# source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec vos valeurs si nécessaire
```

### 4. Lancer les tests

```bash
python -m pytest tests/ -v
```

### 5. Lancer la plateforme Docker

```bash
cd docker
docker-compose up -d
```

## Services & Ports

| Service | URL | Credentials |
|---|---|---|
| Airflow UI | http://localhost:8080 | admin / admin |
| MinIO Console | http://localhost:9101 | minioadmin / minioadmin |
| FastAPI Swagger | http://localhost:8090/docs | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |
| pgAdmin | http://localhost:5050 | admin@admin.com / admin |
| dbt docs | http://localhost:8085 | — |
| PostgreSQL Source | localhost:5432 | admin / admin |

## Contributing


### Convention de commits

[ESP-D1] init: setup repository and gitignore
[ESP-D2] feat: add project structure and Python env
[ESP-D3] infra: containerize data environment
```

### Processus Pull Request

1. Créer une branche `feature/` depuis `dev`
2. Commiter avec la clé Jira
3. Ouvrir une PR vers `dev` (minimum 1 reviewer requis)
4. Merge après approbation
5. `dev` → `main` via PR protégée

## Data Guidelines

> **Règle stricte** : aucune donnée brute ne doit être commitée dans le dépôt.

- `data/raw/` est en **lecture seule** — jamais modifié par les scripts
- `data/processed/` contient les données transformées (gitignored)
- Aucun fichier `.csv`, `.parquet`, `.db` dans le repo
- Aucun secret en clair — utiliser `.env` (gitignored)

## Répartition des Tables Olist

| Source | Tables | Mode d'ingestion |
|---|---|---|
| CSV (Legacy) | `geolocation`, `category_translation` | Full Refresh |
| PostgreSQL (OLTP) | `orders`, `order_items`, `order_payments`, `customers`, `order_reviews` | Incremental (watermark) |
| REST API (FastAPI) | `products`, `sellers` | Full Refresh (paginé) |

---

**Auteur** : Hamza EL OUALI  
