import os
import duckdb
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

DUCKDB_PATH = os.getenv('DUCKDB_DATABASE_PATH', 'data/processed/warehouse.duckdb')

GOLD_TABLES = [
    'dim_date', 'dim_products', 'dim_customers', 'dim_sellers',
    'fct_orders', 'fct_order_items', 'fct_order_reviews',
    'mart_ml_prediction_master', 'mart_customer_scoring',
    'vw_sales_performance', 'vw_logistics_sla',
    'vw_customer_sentiment', 'vw_customer_risk_360',
]


def _pg_connect(host, port, user, password, db):
    return psycopg2.connect(host=host, port=int(port), user=user, password=password, dbname=db)


def export_table(duck_conn, pg_conn, table_name):
    """Exporte une table DuckDB vers le schéma gold de PostgreSQL via psycopg2."""
    try:
        df = duck_conn.execute(f'SELECT * FROM "{table_name}"').df()
        if df.empty:
            logger.warning(f"{table_name}: vide, skip.")
            return

        columns = list(df.columns)
        col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
        cols_quoted = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))

        with pg_conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS gold;")
            cur.execute(f'DROP TABLE IF EXISTS gold."{table_name}"')
            cur.execute(f'CREATE TABLE gold."{table_name}" ({col_defs})')

            rows = [tuple(str(v) if v is not None else None for v in row) for row in df.itertuples(index=False)]
            psycopg2.extras.execute_values(
                cur,
                f'INSERT INTO gold."{table_name}" ({cols_quoted}) VALUES %s',
                rows,
                page_size=5000,
            )

        pg_conn.commit()
        logger.info(f"OK  {table_name} — {len(df):,} lignes exportées vers gold.")

    except Exception as e:
        pg_conn.rollback()
        logger.error(f"ERR {table_name}: {e}")
        raise


def export_gold_to_postgres():
    logger.info(f"Connexion DuckDB: {DUCKDB_PATH}")
    duck_conn = duckdb.connect(DUCKDB_PATH, read_only=True)

    pg_local = _pg_connect(
        host=os.getenv('POSTGRES_DWH_HOST', 'localhost'),
        port=os.getenv('POSTGRES_DWH_PORT', '5433'),
        user=os.getenv('POSTGRES_DWH_USER', 'admin'),
        password=os.getenv('POSTGRES_DWH_PASSWORD', 'admin'),
        db=os.getenv('POSTGRES_DWH_DB', 'dwh_db'),
    )

    try:
        for table in GOLD_TABLES:
            logger.info(f"Export: {table}")
            export_table(duck_conn, pg_local, table)

        logger.info("Export Gold → PostgreSQL terminé avec succès.")

    finally:
        duck_conn.close()
        pg_local.close()


if __name__ == "__main__":
    export_gold_to_postgres()
