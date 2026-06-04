"""
Seed postgres_source (OLTP) avec les fichiers CSV.
Crée les tables avec les types corrects du Schema Registry (int64 → BIGINT, etc.)
pour que le DriftDetector ne détecte pas de faux drifts.
"""
import os
import sys
import time
import psycopg2
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.quality.schema_registry import SCHEMAS, PYARROW_TO_PG
import pyarrow as pa


OLTP_TABLES = ["customers", "orders", "order_items", "order_payments", "order_reviews"]


def _connect():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_SOURCE_HOST", "localhost"),
        port=os.getenv("POSTGRES_SOURCE_PORT", "5434"),
        user=os.getenv("POSTGRES_SOURCE_USER", "admin"),
        password=os.getenv("POSTGRES_SOURCE_PASSWORD", "admin"),
        dbname=os.getenv("POSTGRES_SOURCE_DB", "oltp_db"),
    )


def _ddl_for_table(table_name: str) -> str:
    """Génère le DDL avec les types corrects depuis le Schema Registry."""
    schema = SCHEMAS[table_name]
    cols = []
    for field in schema:
        pg_type = PYARROW_TO_PG.get(field.type, "TEXT")
        cols.append(f'    "{field.name}" {pg_type}')
    return f'CREATE TABLE "{table_name}" (\n' + ",\n".join(cols) + "\n);"


def seed_database():
    host = os.getenv("POSTGRES_SOURCE_HOST", "localhost")
    port = os.getenv("POSTGRES_SOURCE_PORT", "5434")
    print(f"Connecting to postgres_source ({host}:{port})...")
    conn = _connect()
    conn.autocommit = False
    cur = conn.cursor()
    print("Connected successfully!")

    data_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "postgres_source")
    )
    print(f"Data directory: {data_dir}\n")

    for table in OLTP_TABLES:
        path = os.path.join(data_dir, f"{table}.csv")
        if not os.path.exists(path):
            print(f"SKIP  {table} — fichier introuvable : {path}")
            continue

        print(f"Loading {table}.csv ...")
        start = time.time()
        try:
            cur.execute(f'DROP TABLE IF EXISTS "{table}"')
            ddl = _ddl_for_table(table)
            cur.execute(ddl)

            with open(path, "r", encoding="utf-8") as f:
                cur.copy_expert(
                    f'COPY "{table}" FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING \'UTF8\', NULL \'\')',
                    f,
                )

            conn.commit()
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cur.fetchone()[0]
            elapsed = time.time() - start
            print(f"  OK  {table} — {count:,} rows en {elapsed:.1f}s")

        except Exception as e:
            conn.rollback()
            print(f"  ERR {table}: {e}")

    cur.close()
    conn.close()
    print("\nDatabase seeding terminé.")


if __name__ == "__main__":
    seed_database()
