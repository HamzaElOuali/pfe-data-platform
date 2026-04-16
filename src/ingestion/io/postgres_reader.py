"""
ReadFromPostgres — DoFn Apache Beam pour la lecture depuis PostgreSQL source.

Supporte la lecture full refresh et incrémentale (via watermark).
"""
import os
import logging
import psycopg2
import psycopg2.extras
import apache_beam as beam
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ReadFromPostgres(beam.DoFn):
    """
    DoFn qui exécute une requête SQL sur postgres_source
    et yield chaque ligne sous forme de dictionnaire.

    Args:
        query: Requête SQL à exécuter (ex: "SELECT * FROM customers")
    """

    def __init__(self, query: str):
        self.query = query
        self.conn = None

    def setup(self):
        """Ouvre la connexion PostgreSQL au démarrage du worker."""
        self.conn = psycopg2.connect(
            host=os.getenv("POSTGRES_SOURCE_HOST", "localhost"),
            port=os.getenv("POSTGRES_SOURCE_PORT", "5434"),
            user=os.getenv("POSTGRES_SOURCE_USER", "admin"),
            password=os.getenv("POSTGRES_SOURCE_PASSWORD", "admin"),
            dbname=os.getenv("POSTGRES_SOURCE_DB", "oltp_db"),
        )

    def process(self, element):
        """Exécute la requête et yield chaque ligne comme dict."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            logger.info(f"Executing query: {self.query[:100]}...")
            cur.execute(self.query)
            for row in cur:
                yield dict(row)
        except Exception as e:
            logger.error(f"Failed to read from postgres_source: {e}")
            raise
        finally:
            cur.close()

    def teardown(self):
        """Ferme la connexion PostgreSQL."""
        if self.conn:
            self.conn.close()
