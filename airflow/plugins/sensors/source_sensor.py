"""
Source Health Sensors — Vérifie la disponibilité des sources avant l'ingestion.
"""
import os
import requests
import psycopg2
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults

class PostgresHealthSensor(BaseSensorOperator):
    """Vérifie si une base PostgreSQL est accessible."""
    @apply_defaults
    def __init__(self, conn_id_env_prefix, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = conn_id_env_prefix

    def poke(self, context):
        try:
            host = os.getenv(f"{self.prefix}_HOST")
            port = os.getenv(f"{self.prefix}_PORT")
            user = os.getenv(f"{self.prefix}_USER")
            password = os.getenv(f"{self.prefix}_PASSWORD")
            dbname = os.getenv(f"{self.prefix}_DB")
            
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, dbname=dbname,
                connect_timeout=5
            )
            conn.close()
            return True
        except Exception as e:
            self.log.info(f"Postgres {self.prefix} not ready: {e}")
            return False

class APIHealthSensor(BaseSensorOperator):
    """Vérifie si l'API FastAPI est accessible."""
    @apply_defaults
    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url

    def poke(self, context):
        try:
            response = requests.get(f"{self.url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.log.info(f"API not ready at {self.url}: {e}")
            return False
