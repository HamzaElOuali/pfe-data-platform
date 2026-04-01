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

# Copier et installer les dépendances Python
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Répertoire de travail
WORKDIR /opt/airflow
