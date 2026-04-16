"""
WriteToBronze — DoFn Apache Beam pour l'écriture batch dans PostgreSQL DWH.

Utilise psycopg2.extras.execute_values() pour des insertions performantes.
Les colonnes sont définies explicitement par le Schema Registry (pas d'inférence).
"""
import os
import logging
import psycopg2
import psycopg2.extras
import apache_beam as beam
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class WriteToBronze(beam.DoFn):
    """
    DoFn qui accumule des éléments (dicts) et les écrit en batch
    dans une table du schéma bronze de postgres_dwh.

    Args:
        table_name: Nom de la table cible (ex: "geolocation")
        schema_name: Schéma PostgreSQL (default: "bronze")
        batch_size: Nombre de lignes par batch INSERT (default: 1000)
    """

    def __init__(self, table_name: str, schema_name: str = "bronze", batch_size: int = 1000):
        self.table_name = table_name
        self.schema_name = schema_name
        self.batch_size = batch_size
        self.buffer = []
        self.conn = None
        self.columns = None

    def setup(self):
        """Ouvre la connexion PostgreSQL au démarrage du worker."""
        self.conn = psycopg2.connect(
            host=os.getenv("POSTGRES_DWH_HOST", "localhost"),
            port=os.getenv("POSTGRES_DWH_PORT", "5433"),
            user=os.getenv("POSTGRES_DWH_USER", "admin"),
            password=os.getenv("POSTGRES_DWH_PASSWORD", "admin"),
            dbname=os.getenv("POSTGRES_DWH_DB", "dwh_db"),
        )
        self.conn.autocommit = False

    def process(self, element):
        """Accumule les éléments dans un buffer et flush quand le batch est plein."""
        if self.columns is None:
            self.columns = list(element.keys())

        self.buffer.append(element)

        if len(self.buffer) >= self.batch_size:
            self._flush()

    def finish_bundle(self):
        """Flush le buffer restant à la fin du bundle."""
        if self.buffer:
            self._flush()

    def _flush(self):
        """Écrit le buffer dans PostgreSQL via execute_values."""
        if not self.buffer or not self.conn:
            return

        cur = self.conn.cursor()
        full_table = f"{self.schema_name}.{self.table_name}"
        cols = ", ".join(self.columns)
        template = "(" + ", ".join([f"%({c})s" for c in self.columns]) + ")"

        try:
            psycopg2.extras.execute_values(
                cur,
                f"INSERT INTO {full_table} ({cols}) VALUES %s",
                self.buffer,
                template=template,
                page_size=self.batch_size,
            )
            self.conn.commit()
            logger.info(f"Flushed {len(self.buffer)} rows to {full_table}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to write to {full_table}: {e}")
            raise
        finally:
            cur.close()
            self.buffer = []

    def teardown(self):
        """Ferme la connexion PostgreSQL."""
        if self.conn:
            self.conn.close()
