# E-Commerce Data Platform — PFE Data Engineering

**End-to-end data engineering platform built on the E-Commerce dataset.**  
Covers the full data value chain: ingestion depuis l'API Kaggle → structured storage → ELT transformation → analytical serving.

---

## Overview

This platform was designed and built as a Final Year Engineering Project (PFE), it demonstrates production-grade data engineering practices applied to a real-world e-commerce dataset of ~100,000 orders across 9 relational tables.

The architecture follows the **ELT paradigm** with a clear separation of concerns:

- **Extract & Load** — Apache Beam pipelines ingest data depuis l'API Kaggle into a structured Bronze landing zone (PostgreSQL)
- **Transform** — dbt-core running on DuckDB transforms raw Bronze data into clean Silver models and business-ready Gold aggregations
- **Quality** — A three-level cascade (Drift Detection → GE Validation → dbt Tests) ensures no corrupted data reaches analytical layers
- **Serve** — A read-only Gold layer exposes data to BI tools, SQL analysts, and ML pipelines

---

## Architecture

My architecture leverages **PostgreSQL** for persistent storage (Landing/Bronze) and **DuckDB** as a high-performance OLAP engine for transformations (Silver).

CROSS-CUTTING LAYER
───────────────────
Observability  : Grafana Dashboards
Data Quality   : Great Expectations + dbt tests + DQ Reporter
DataOps        : GitHub Actions CI/CD
Schema Control : PyArrow Schema Registry + Drift Detector

---
## Medallion Architecture

### Bronze Layer — Raw Landing Zone

PostgreSQL schema `bronze` in `postgres_dwh`. Stores raw data exactly as received from source with governance metadata appended by each pipeline:

| Metadata Column | Description |
|---|---|
| `_ingested_at` | UTC timestamp of ingestion |
| `batch_id` | UUID identifying the pipeline run |

Tables are created with **explicit types** defined by the PyArrow Schema Registry — no dynamic schema inference. Full Refresh pipelines truncate before writing to guarantee idempotence.

**Current Bronze volumes:**

| Table | Rows | Source |
|---|---|---|
| geolocation | 1,000,163 |
| product_category_name_translation | 71 |
| orders | 99,441 |
| customers | 99,441 |
| order_items | 112,650 |
| order_payments | 103,886 |
| order_reviews | 99,224 |
| products | 32,951 |
| sellers | 3,095 |

**Total: 1,550,074 rows across 9 tables.**

### Silver Layer — Curated Zone

Produced by dbt-core running on DuckDB via `postgres_scanner`. Each `stg_*` model applies:

- **Type casting** — all timestamps, floats, and integers explicitly cast from TEXT
- **PII masking** — `customer_id`, `customer_unique_id`, `seller_id` hashed via SHA-256; `review_comment_message` replaced by `has_comment` boolean
- **Normalization** — city and state fields uppercased and trimmed
- **Derived columns** — `delivery_days`, `is_late`, `total_value`, `response_hours`
- **Business rule validation** — price ≥ 0, freight ≥ 0, review score ∈ [1,5], coordinates within Brazil bounds
- **Deduplication** — generic `deduplicate` macro using DuckDB `QUALIFY` + `ROW_NUMBER()`
- **NULL handling** — primary key NULLs rejected; `product_category_name` defaulted to `'unknown'`; optional timestamps preserved as NULL

**PII policy:**

| Field | Treatment | Reaches Gold |
|---|---|---|
| `customer_id` | SHA-256 hash | Hash only |
| `customer_unique_id` | SHA-256 hash | Hash only |
| `seller_id` | SHA-256 hash | Hash only |
| `review_comment_message` | Replaced by `has_comment` boolean | Boolean only |

### Gold Layer — Business-Ready SSOT (Sprint 5)

La couche Gold transforme les données nettoyées en **actifs décisionnels**. Elle est structurée selon deux axes :
- **Bus Matrix (Star Schema)** : Dimensions (`dim_`) et Faits (`fct_`) conformés, optimisés pour les jointures BI.
- **AI & Analytics Marts** : Tables larges pour le Machine Learning et Vues sémantiques pour Power BI.

**Architecture de la couche Gold :**
- **Dénormalisation intelligente** : Jointures complexes pré-calculées (ex: Haversine distance client-vendeur).
- **Sécurité finale** : Hachage SHA-256 persistant sur les IDs sensibles.
- **Serving Layer** : Exposition de vues métiers (`vw_`) pour supprimer toute complexité de modélisation côté Analyste.


## Rapport de Fin de Sprint 4 : Industrialisation de la Plateforme

### 1. Pipeline d’Ingestion Automatisé
L’objectif principal de ce sprint était de faire évoluer le pipeline d’une exécution manuelle vers une orchestration automatisée, robuste et sécurisée.

**Orchestration & Flux de Travail**
L’orchestration a été mise en place à l’aide de **Apache Airflow**, via le DAG principal `main_pipeline_dag.py`. Le pipeline suit une logique de sécurité de type **Fail-Fast**, permettant d’arrêter immédiatement l’exécution en cas d’anomalie.

Le flux se déroule comme suit :
*   **Health Checks** : Des capteurs (`APIHealthSensor`) vérifient la disponibilité de la source de données.
*   **Ingestion** : Exécution du pipeline Python (**API Kaggle**) vers la couche Bronze.
*   **Transformation (dbt)** : Lancement des modèles dbt pour alimenter la couche Silver.
*   **Data Quality** : Vérification automatique de la qualité des données avec génération de rapports.

**Automatisation : Trigger vs Cron**
Le pipeline repose principalement sur une planification temporelle (Cron-based scheduling).
*   **Configuration** : `schedule_interval='@daily'`
*   **Fonctionnement** : Exécution automatique quotidienne à minuit.
*   **Flexibilité** : Possibilité de déclenchement manuel (Trigger) via l’interface Airflow pour des besoins de retraitement.

### 2. Normalisation & Enrichissement des Données
Cette étape transforme les données brutes (couche Bronze) en données fiables, structurées et exploitables (couche Silver).

**Stratégies de Nettoyage (Module `normalizer.py`)**
| Technique | Description | Implémentation |
| :--- | :--- | :--- |
| **Imputation** | Remplacement des valeurs manquantes (médiane ou constante) | `fill_missing_numeric`, `fill_missing_categorical` |
| **Gestion des outliers** | Limitation des valeurs extrêmes via la méthode IQR (facteur 1.5) | `cap_outliers_iqr` |
| **Standardisation** | Nettoyage des chaînes (trim, majuscules, regex) | `clean_string`, `clean_zip_code` |

**Détails par Table (Couche Silver)**
*   **stg_orders** : Formatage des dates au format ISO, Standardisation des statuts (majuscules), Calcul automatique des délais de livraison.
*   **stg_products** : Normalisation des noms de catégories, Imputation des valeurs nulles (poids/dimensions → 0).
*   **stg_customers** : Anonymisation des données sensibles (SHA-256), Nettoyage des codes postaux (format standardisé à 5 chiffres).
*   **stg_order_reviews** : Typage strict du score (entier), Enrichissement des commentaires pour traitement NLP.
*   **stg_geolocation** : Filtrage des coordonnées hors zones valides, Suppression des doublons géographiques.

### 3. Data Quality Automatisée
La qualité des données est contrôlée à deux niveaux : Niveau structurel via dbt (tests de schéma) et Niveau métier via un moteur de règles personnalisé.

**Tests de Qualité par Table**
| Table | Tests dbt (Schéma) | Tests Métier (DQ Rules) |
| :--- | :--- | :--- |
| **Toutes les tables** | `unique`, `not_null` sur les clés primaires | Complétude des colonnes critiques |
| **stg_orders** | `accepted_values` (statuts valides) | Fraîcheur des données (< 24h) |
| **stg_order_items** | `accepted_range` (prix > 0) | Validation du format des identifiants |
| **stg_order_payments** | `accepted_range` (montant ≥ 0) | Cohérence des types de paiement |
| **stg_order_reviews** | `accepted_range` (score entre 1 et 5) | Détection des messages vides |

### Détails de la Couverture de Tests (21 points de contrôle)
Pour garantir une fiabilité de 100% sur les données exposées, nous avons configuré une suite de **21 tests automatisés** répartis sur l'ensemble du schéma Silver :

1.  **Gestion des Identifiants (14 tests)** : 
    *   Tests d'unicité (`unique`) et de complétude (`not_null`) sur les clés primaires des tables : `orders`, `customers`, `products`, `reviews`, `sellers`, `geolocation`, et `category_translation`.
2.  **Intégrité des Flux (3 tests)** : 
    *   Validation `not_null` sur les clés étrangères de la table `order_items` (order_id, product_id) et `order_payments` (order_id) pour garantir que chaque ligne est rattachée à une entité parente.
3.  **Validité des Domaines Métier (4 tests)** :
    *   **Statuts** (`stg_orders`) : Un test `accepted_values` vérifie que les statuts appartiennent exclusivement à la liste officielle (DELIVERED, SHIPPED, etc.).
    *   **Finance** (`stg_order_items` & `stg_order_payments`) : Deux tests `accepted_range` (min: 0) bloquent toute valeur négative sur les prix et les montants payés.
    *   **Satisfaction** (`stg_order_reviews`) : Un test `accepted_range` (1 à 5) valide la cohérence des notes attribuées par les clients.

## Rapport de Fin de Sprint 5 : Architecture Gold & Serving Layer

L'objectif de ce sprint était d'industrialiser l'exposition des données et de préparer le terrain pour l'Intelligence Artificielle.

### 1. Implémentation du Bus Matrix (Star Schema)
Nous avons adopté une modélisation dimensionnelle (Kimball) pour garantir une "Source Unique de Vérité" (SSOT) :
- **Dimensions** : `dim_customers` (Géo-enrichi), `dim_sellers` (Sécurisé), `dim_products` (Traduit), `dim_date`.
- **Faits** : `fct_orders` (SLA/Logistique), `fct_order_items` (Ventes), `fct_order_reviews` (Satisfaction).

### 2. Préparation à l'IA (Machine Learning Marts)
Création de tables de "Serving" prêtes pour les algorithmes prédictifs :
- **mart_ml_prediction_master** : Feature store consolidant 20+ variables (Distance Haversine, poids, délais, géographie).
- **mart_customer_scoring** : Moteur de segmentation calculant des scores de risque (Churn) et des segments (VIP, At Risk) via des règles métier SQL.

### 3. Analytics Serving Layer (Power BI Ready)
Pour simplifier le travail des analystes, nous avons créé une couche de vues dénormalisées (One Big Table) :
- `vw_sales_performance` : Analyse du CA et rentabilité.
- `vw_logistics_sla` : Monitoring des retards et performance transporteurs.
- `vw_customer_sentiment` : Corrélation entre logistique et satisfaction (VoC).
- `vw_customer_risk_360` : Pilotage proactif de la rétention client.

### 4. Industrialisation de l'Export
Mise en place d'un script automatisé (`gold_exporter.py`) permettant de synchroniser les 13 actifs Gold (tables et vues) de DuckDB vers le schéma `gold` de PostgreSQL, assurant la persistance et l'accès concurrent aux données.

### 5. Cloud Infrastructure & Streaming (GCP)
L'extension de la plateforme vers le cloud permet de gérer des flux en temps réel et d'assurer une scalabilité horizontale :
*   **Infrastructure as Code (Terraform)** : Provisioning automatisé des ressources GCP via les fichiers de configuration dans `terraform/`.
    *   **Compute Engine** : Déploiement d'une instance VM dédiée (`e2-medium`) pour l'hébergement des services **Kafka** (broker de messages) et **Spark** (traitement de flux).
    *   **Cloud Storage (GCS)** : Création d'un bucket sécurisé pour le stockage des checkpoints Spark et la persistance du Data Lake.
    *   **Networking & Sécurité** : Configuration d'une IP statique et de règles de Firewall (port 9092) pour l'exposition sécurisée du broker Kafka.
*   **Pipeline Hybride** : Architecture flexible permettant de basculer l'exécution entre un environnement local (Docker) et le Cloud (GCP) selon les besoins de performance.

---


**Rapports et Monitoring**
*   **Rapport JSON** : Génération d’un fichier horodaté dans `data/processed/dq_reports/` pour chaque exécution.
*   **Rapport Markdown** : Fichier `dq_report_latest.md` offrant une vue lisible avec indicateurs [PASS/FAIL].
*   **Persistance SQL** : Insertion des métriques dans la table `quality.dq_metrics` pour visualisation dans Grafana.
*   **Seuil de validation** : Échec automatique du pipeline si le score global de qualité est inférieur à **90%**.

---

## Technology Stack

| Layer | Technology | Version | Role |
|---|---|---|---|
| Ingestion | Apache Beam (DirectRunner) | 2.54.0 | Ingestion automatique depuis l'API Kaggle |
| Storage | PostgreSQL | 15 | Structured landing zone (Bronze) |
| Compute | DuckDB | 0.10.3 | OLAP analytical engine via `postgres_scanner` |
| Transformation | dbt-core + dbt-duckdb | 1.7.x | ELT Bronze → Silver → Gold |
| Orchestration | Apache Airflow | 2.9.1 | DAG scheduling, retry, SLA monitoring |
| Data Quality | Great Expectations + dbt tests | 0.18.19 | Entry validation + model integrity |
| Monitoring | Grafana | latest | Data quality and infrastructure dashboards |
| Catalog | dbt docs | — | Lineage graph, model documentation |
| Containerization | Docker Compose v2 | — | Self-contained Phase A platform |
| Infrastructure | Terraform | latest | Infrastructure as Code (IaC) pour GCP |
| Cloud Provider | Google Cloud (GCP) | — | Hébergement VM, GCS Buckets et Networking |

---

## Data Sources

| Source | Tables | Pattern | Justification |
|---|---|---|---|
| **API Kaggle** | `orders`, `customers`, `products`, `items`, etc. | Full Load | Transactional e-commerce data |

---

## Project Structure

```bash
pfe-data-platform/
│
├── airflow/
│   ├── dags/                        # DAG definitions (main_pipeline_dag.py) & (kaggle_pipeline_dag.py)
│   ├── logs/                        # Airflow execution logs (gitignored)
│   └── plugins/                     # Custom Airflow plugins & Sensors
│
├── api/
│   ├── main.py                      # FastAPI mock — /products, /sellers, /health
│   └── data/                        # CSV files served by the API
│
├── data/
│   ├── raw/                         # Source datasets (read-only)
│   └── processed/
│       ├── watermarks.json          # Incremental watermark state (gitignored)
│       └── dq_reports/              # Quality reports (JSON, Markdown)
│
├── dbt/
│   ├── models/
│   │   ├── silver/                  # staging models (stg_*)
│   │   └── gold/                    # Facts, dimensions, marts
│   │       └── analytics/           # Business Views (vw_*) for Power BI
│   ├── macros/
│   │   ├── clean_string.sql         # String cleaning macro
│   │   ├── coalesce_default.sql     # Null handling macro
│   │   └── deduplicate.sql          # Generic deduplication macro
│   ├── profiles.yml                 # DuckDB connection profile
│   ├── dbt_project.yml              # Project configuration
│   └── packages.yml                 # dbt-utils dependency
│
├── docker/
│   ├── docker-compose.yml           # Full platform — 10 services
│   ├── Dockerfile                   # Airflow image + Python dependencies
│   ├── Dockerfile.dbt               # dbt-docs image (catalog on port 8085)
│   └── monitoring/                  # Observability configs
│       └── grafana/
│           ├── datasources/         # PostgreSQL auto-provisioning
│           └── dashboards/          # Data Quality dashboard (JSON)
│
├── src/
│   ├── ingestion/
│   │   ├── kaggle_ingestor.py           # Kaggle API Ingestion pipeline
│   │   └── io/
│   │       ├── postgres_writer.py       # Reusable WriteToBronze DoFn
│   │       └── postgres_reader.py       # Reusable ReadFromPostgres DoFn
│   ├── processing/
│   │   ├── normalizer.py                # Imputation & Outliers management
│   │   └── gold_exporter.py             # DuckDB → PostgreSQL (Gold Sync)
│   ├── quality/
│   │   ├── schema_registry.py           # PyArrow schema contracts
│   │   ├── ge_validator.py              # GE validation DoFn
│   │   ├── dq_rules.py                  # Custom DQ Rules Engine
│   │   └── dq_reporter.py               # DQ score computation → quality.dq_metrics
│   └── scripts/
│       ├── init_bronze_schema.py        # Bronze schema initialization
│       └── seed_oltp.py                 # Seeds source from CSV files
│
├── terraform/
│   ├── main.tf                      # Ressources GCP (VM, Bucket, Firewall)
│   ├── variables.tf                 # Configuration du projet et de la région
│   └── terraform.tfvars             # Variables spécifiques à l'environnement
├── tests/                           # pytest unit and integration tests
├── .env.example                     # Environment variable template
├── requirements.txt                 # Production Python dependencies
└── requirements-dev.txt             # Dev dependencies
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop 24+ with Docker Compose v2
- Git

### 1. Clone the repository

```bash
git clone https://github.com/HamzaElOuali/pfe-data-platform.git
cd pfe-data-platform
```

### 2. Configure Python environment

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Set environment variables

```bash
cp .env.example .env
# Edit .env with your credentials — never commit this file
```

### 4. Seed the source database

```bash
python -m src.scripts.seed_oltp
```

### 5. Initialize the Bronze schema

```bash
python -m src.scripts.init_bronze_schema
```

### 6. Start the platform

```bash
cd docker
docker-compose up -d
```

---

## Services

Une fois la plateforme lancée, les interfaces suivantes sont disponibles :

| Service | URL | Description |
|---|---|---|
| Airflow UI | http://localhost:8080 | Orchestration et monitoring des pipelines |
| FastAPI Swagger | http://localhost:8090/docs | Documentation du mock API |
| dbt Catalog | http://localhost:8085 | Lineage et documentation des modèles |
| Grafana | http://localhost:3000 | Dashboards de Data Quality et infrastructure |
| pgAdmin | http://localhost:5050 | Administration PostgreSQL |

---

## Data Quality & Governance

Nous implémentons un processus de validation rigoureux :
- **Anonymisation** : Les données PII sont hachées via SHA256 dans la couche Silver.
- **Deduplication** : Des macros dbt génériques assurent l'unicité avant matérialisation.
- **DQ Scoring** : Notre script `dq_reporter.py` calcule un **Score de Qualité Global** stocké dans `quality.dq_metrics` et des scores détaillés par domaine.

---

## Author

**Hamza EL OUALI**  
