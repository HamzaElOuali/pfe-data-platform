"""
Pipeline 1 — CSV to Bronze (Full Refresh)

Lit les fichiers CSV legacy depuis data/raw/csv_source/,
ajoute les métadonnées d'ingestion, valide via GE,
et charge dans le schéma bronze de postgres_dwh.

Tables : geolocation, product_category_name_translation

Usage :
    python -m src.ingestion.pipeline_csv_to_bronze
"""
import os
import csv
import logging
import psycopg2
from datetime import datetime, timezone

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

from src.ingestion.io.postgres_writer import WriteToBronze
from src.quality.ge_validator import ValidateWithGE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Répertoire des fichiers CSV source
CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "csv_source")
CSV_DIR = os.path.normpath(CSV_DIR)

# Configuration des fichiers CSV à ingérer
CSV_FILES = {
    "geolocation": {
        "filename": "geolocation.csv",
        "pk_columns": ["geolocation_zip_code_prefix"],
    },
    "product_category_name_translation": {
        "filename": "product_category_name_translation.csv",
        "pk_columns": ["product_category_name"],
    },
}


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


def parse_csv_file(file_config):
    """
    Générateur : lit un fichier CSV et yield chaque ligne comme dict
    avec les métadonnées Bronze ajoutées.
    """
    filepath = os.path.join(CSV_DIR, file_config["filename"])
    table_name = file_config["table_name"]
    ingested_at = datetime.now(timezone.utc).isoformat()

    logger.info(f"Reading CSV: {filepath}")

    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    for encoding in encodings:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["_ingested_at"] = ingested_at
                    row["_source_file"] = file_config["filename"]
                    row["_batch_id"] = None
                    row["_api_version"] = None
                    yield row
            return
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Cannot decode {filepath} with utf-8 or latin-1")


def run():
    """Exécute le Pipeline 1 : CSV → Bronze."""
    options = PipelineOptions(runner="DirectRunner")

    for table_name, config in CSV_FILES.items():
        config["table_name"] = table_name
        filepath = os.path.join(CSV_DIR, config["filename"])

        if not os.path.exists(filepath):
            logger.warning(f"SKIP — fichier introuvable : {filepath}")
            continue

        # Nettoyage avant ingestion
        truncate_table(table_name)

        logger.info(f"=== Pipeline CSV → Bronze : {table_name} ===")

        with beam.Pipeline(options=options) as p:
            (
                p
                | f"Read_{table_name}" >> beam.Create([config])
                | f"Parse_{table_name}" >> beam.FlatMap(parse_csv_file)
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

        logger.info(f"=== OK — {table_name} ingéré dans bronze ===\n")

    logger.info("Pipeline 1 (CSV → Bronze) terminé.")


if __name__ == "__main__":
    run()

