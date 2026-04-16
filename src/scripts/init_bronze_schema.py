"""
Initialisation du schéma Bronze dans postgres_dwh.
Crée le schéma 'bronze' et les 9 tables avec des types explicites
définis par le Schema Registry PyArrow.

Usage :
    python -m src.scripts.init_bronze_schema
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Ajouter le répertoire racine au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.quality.schema_registry import SCHEMAS, get_pg_create_table


def init_bronze():
    """Crée le schéma bronze et toutes les tables dans postgres_dwh."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_DWH_HOST", "localhost"),
        port=os.getenv("POSTGRES_DWH_PORT", "5433"),
        user=os.getenv("POSTGRES_DWH_USER", "admin"),
        password=os.getenv("POSTGRES_DWH_PASSWORD", "admin"),
        dbname=os.getenv("POSTGRES_DWH_DB", "dwh_db"),
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Créer le schéma bronze
    print("Creating schema 'bronze'...")
    cur.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    print("  OK  schema bronze created.")

    # Créer les 9 tables Bronze
    for table_name in SCHEMAS:
        ddl = get_pg_create_table(table_name)
        print(f"Creating table bronze.{table_name}...")
        cur.execute(ddl)
        print(f"  OK  bronze.{table_name} ready.")

    cur.close()
    conn.close()
    print(f"\nBronze initialization complete — {len(SCHEMAS)} tables created.")


if __name__ == "__main__":
    init_bronze()
