# ══════════════════════════════════════════════════════════════
# PFE Data Platform — Dockerfile (Airflow + Data dependencies)
# ══════════════════════════════════════════════════════════════
FROM apache/airflow:2.9.1-python3.11

USER root

# Installer les dépendances système nécessaires
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    curl \
    && update-ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Étape 1 — Packages Airflow/Beam/dbt compatibles (numpy 1.26.x Airflow constraint)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Étape 2 — Packages ML + upgrade numpy 2.x (séparé pour bypasser les contraintes Airflow)
# numpy 2.x est requis pour charger les pkl sauvegardés avec numpy 2.x (numpy._core)
RUN pip install --no-cache-dir \
    "numpy>=2.0.0" \
    "pyarrow>=16.0.0,<17.0.0" \
    "joblib>=1.3.0" \
    "scikit-learn>=1.3.0" \
    "xgboost>=2.0.0" \
    "lightgbm>=4.0.0"

# Répertoire de travail
WORKDIR /opt/airflow
