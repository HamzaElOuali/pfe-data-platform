"""
Pipeline 3 — FastAPI REST to Bronze (Full Refresh paginé)

Effectue des requêtes HTTP GET paginées sur les endpoints FastAPI,
ajoute les métadonnées d'ingestion, valide via GE,
et charge dans le schéma bronze de postgres_dwh.

Tables : products, sellers

Usage :
    python -m src.ingestion.pipeline_api_to_bronze
"""
import os
import logging
import psycopg2
from datetime import datetime, timezone

import requests
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

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


# Configuration de l'API
API_BASE_URL = os.getenv("FASTAPI_MOCK_URL", "http://fastapi_mock:80")
API_VERSION = "v1.0"
PAGE_SIZE = 500

# Configuration des endpoints à ingérer
API_ENDPOINTS = {
    "products": {
        "path": "/products",
        "pk_columns": ["product_id"],
    },
    "sellers": {
        "path": "/sellers",
        "pk_columns": ["seller_id"],
    },
}


class FetchPaginatedAPI(beam.DoFn):
    """
    DoFn qui effectue des requêtes GET paginées sur un endpoint FastAPI
    et yield chaque enregistrement comme dict.

    Args:
        endpoint_path: Chemin de l'endpoint (ex: "/products")
        page_size: Nombre d'éléments par page (default: 500)
    """

    def __init__(self, endpoint_path: str, page_size: int = PAGE_SIZE):
        self.endpoint_path = endpoint_path
        self.page_size = page_size

    def process(self, element):
        """Itère sur toutes les pages de l'API et yield chaque record."""
        page = 1
        total_fetched = 0

        while True:
            url = f"{API_BASE_URL}{self.endpoint_path}?page={page}&size={self.page_size}"
            logger.info(f"GET {url}")

            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                payload = response.json()
            except requests.RequestException as e:
                logger.error(f"API request failed: {e}")
                raise

            records = payload.get("data", [])
            if not records:
                logger.info(f"No more data at page {page}. Total fetched: {total_fetched}")
                break

            for record in records:
                total_fetched += 1
                yield record

            # Vérifier si on a atteint la dernière page
            total_pages = payload.get("total_pages", 1)
            if page >= total_pages:
                logger.info(f"Reached last page ({page}/{total_pages}). Total: {total_fetched}")
                break

            page += 1


def add_api_metadata(element):
    """Ajoute les métadonnées Bronze pour les données API."""
    element["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    element["_source_file"] = None
    element["_batch_id"] = None
    element["_api_version"] = API_VERSION
    return element


def run():
    """Exécute le Pipeline 3 : API → Bronze."""
    options = PipelineOptions(runner="DirectRunner")

    for table_name, config in API_ENDPOINTS.items():
        # Nettoyage avant ingestion
        truncate_table(table_name)

        logger.info(f"=== Pipeline API → Bronze : {table_name} ===")

        with beam.Pipeline(options=options) as p:
            (
                p
                | f"Start_{table_name}" >> beam.Create(["trigger"])
                | f"Fetch_{table_name}" >> beam.ParDo(
                    FetchPaginatedAPI(endpoint_path=config["path"])
                )
                | f"Metadata_{table_name}" >> beam.Map(add_api_metadata)
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

    logger.info("Pipeline 3 (API → Bronze) terminé.")


if __name__ == "__main__":
    run()
