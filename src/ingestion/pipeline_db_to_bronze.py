"""
Pipeline 2 — PostgreSQL OLTP to Bronze (Incremental pour orders, Full Refresh pour les autres)

Lit les tables depuis postgres_source (simulateur OLTP),
ajoute les métadonnées d'ingestion, valide via GE,
et charge dans le schéma bronze de postgres_dwh.

Tables : customers, orders, order_items, order_payments, order_reviews

Usage :
    python -m src.ingestion.pipeline_db_to_bronze
"""
import os
import json
import uuid
import logging
import psycopg2
from datetime import datetime, timezone

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

from src.ingestion.io.postgres_reader import ReadFromPostgres
from src.ingestion.io.postgres_writer import WriteToBronze
from src.quality.ge_validator import ValidateWithGE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def truncate_table(table_name):
    """Vide la table cible avant l'ingestion (Full Refresh)."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_DWH_HOST", "localhost"),
        port=os.getenv("POSTGRES_DWH_PORT", "5433"),
        user=os.getenv("POSTGRES_DWH_USER", "admin"),
        password=os.getenv("POSTGRES_DWH_PASSWORD", "admin"),
        dbname=os.getenv("POSTGRES_DWH_DB", "dwh_db"),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        logger.info(f"TRUNCATE table bronze.{table_name}...")
        cur.execute(f"TRUNCATE TABLE bronze.{table_name} RESTART IDENTITY CASCADE;")
    conn.close()


# Fichier watermark pour le suivi incrémental
WATERMARK_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "watermarks.json"
)
WATERMARK_FILE = os.path.normpath(WATERMARK_FILE)

# Configuration des tables OLTP à ingérer
OLTP_TABLES = {
    "customers": {
        "query": "SELECT * FROM customers",
        "mode": "full_refresh",
        "pk_columns": ["customer_id"],
    },
    "orders": {
        "query": "SELECT * FROM orders",
        "mode": "full_refresh",
        "pk_columns": ["order_id"],
    },
    "order_items": {
        "query": "SELECT * FROM order_items",
        "mode": "full_refresh",
        "pk_columns": ["order_id", "order_item_id"],
    },
    "order_payments": {
        "query": "SELECT * FROM order_payments",
        "mode": "full_refresh",
        "pk_columns": ["order_id", "payment_sequential"],
    },
    "order_reviews": {
        "query": "SELECT * FROM order_reviews",
        "mode": "full_refresh",
        "pk_columns": ["review_id"],
    },
}


def load_watermarks() -> dict:
    """Charge les watermarks depuis le fichier JSON."""
    if os.path.exists(WATERMARK_FILE):
        with open(WATERMARK_FILE, "r") as f:
            return json.load(f)
    return {}


def save_watermarks(watermarks: dict):
    """Sauvegarde les watermarks dans le fichier JSON."""
    os.makedirs(os.path.dirname(WATERMARK_FILE), exist_ok=True)
    with open(WATERMARK_FILE, "w") as f:
        json.dump(watermarks, f, indent=2)


def build_query(table_name: str, config: dict, watermarks: dict) -> str:
    """Construit la requête SQL, avec filtre watermark si incrémental."""
    base_query = config["query"]

    if config["mode"] == "incremental":
        wm_col = config["watermark_column"]
        last_wm = watermarks.get(table_name)
        if last_wm:
            logger.info(f"Incremental mode — watermark: {wm_col} > '{last_wm}'")
            return f"{base_query} WHERE {wm_col} > '{last_wm}' ORDER BY {wm_col}"
        else:
            logger.info(f"Incremental mode — first run (no watermark), full load.")
            return f"{base_query} ORDER BY {wm_col}"

    return base_query


def add_db_metadata(element):
    """Ajoute les métadonnées Bronze pour les données OLTP."""
    element["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    element["_source_file"] = None
    element["_batch_id"] = add_db_metadata.batch_id
    element["_api_version"] = None
    return element


def run():
    """Exécute le Pipeline 2 : OLTP → Bronze."""
    options = PipelineOptions(runner="DirectRunner")
    watermarks = load_watermarks()
    batch_id = str(uuid.uuid4())[:8]
    add_db_metadata.batch_id = batch_id

    logger.info(f"Batch ID: {batch_id}")

    for table_name, config in OLTP_TABLES.items():
        # Nettoyage avant ingestion si Full Refresh
        if config["mode"] == "full_refresh":
            truncate_table(table_name)

        query = build_query(table_name, config, watermarks)
        logger.info(f"=== Pipeline OLTP → Bronze : {table_name} ===")
        logger.info(f"Query: {query[:120]}...")

        with beam.Pipeline(options=options) as p:
            (
                p
                | f"Start_{table_name}" >> beam.Create([query])
                | f"Read_{table_name}" >> beam.ParDo(ReadFromPostgres(query))
                | f"Metadata_{table_name}" >> beam.Map(add_db_metadata)
                | f"Validate_{table_name}" >> beam.ParDo(
                    ValidateWithGE(
                        table_name=table_name,
                        pk_columns=config["pk_columns"],
                    )
                )
                | f"Write_{table_name}" >> beam.ParDo(
                    WriteToBronze(table_name=table_name)
                )
            )

        # Mettre à jour le watermark après succès (incremental uniquement)
        if config["mode"] == "incremental":
            watermarks[table_name] = datetime.now(timezone.utc).isoformat()
            save_watermarks(watermarks)
            logger.info(f"Watermark updated for {table_name}")

        logger.info(f"=== OK — {table_name} ingéré dans bronze ===\n")

    logger.info("Pipeline 2 (OLTP → Bronze) terminé.")


if __name__ == "__main__":
    run()
