import duckdb
import os
import logging
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def export_gold_to_postgres():
    """
    Exports Gold layer tables from DuckDB to PostgreSQL.
    Ensures the 'gold' schema exists in the destination database.
    """
    load_dotenv()
    
    db_path = os.getenv('DUCKDB_DATABASE_PATH', 'data/processed/warehouse.duckdb')
    pg_host = os.getenv('POSTGRES_DWH_HOST', 'localhost')
    pg_port = os.getenv('POSTGRES_DWH_PORT', '5433')
    pg_user = os.getenv('POSTGRES_DWH_USER', 'admin')
    pg_pass = os.getenv('POSTGRES_DWH_PASSWORD', 'admin')
    pg_db = os.getenv('POSTGRES_DWH_DB', 'dwh_db')

    logger.info(f"Connecting to DuckDB: {db_path}")
    conn = duckdb.connect(db_path)
    
    try:
        logger.info("Loading PostgreSQL extension...")
        conn.execute("INSTALL postgres; LOAD postgres;")
        
        pg_conn_str = f"host={pg_host} port={pg_port} user={pg_user} password={pg_pass} dbname={pg_db}"
        conn.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE postgres);")
        
        logger.info("Ensuring 'gold' schema exists in PostgreSQL...")
        conn.execute("CREATE SCHEMA IF NOT EXISTS pg.gold;")
        
        gold_tables = [
            'dim_date', 'dim_products', 'dim_customers', 'dim_sellers',
            'fct_orders', 'fct_order_items', 'fct_order_reviews',
            'mart_ml_prediction_master', 'mart_customer_scoring',
            'vw_sales_performance', 'vw_logistics_sla', 
            'vw_customer_sentiment', 'vw_customer_risk_360'
        ]
        
        for table in gold_tables:
            logger.info(f"Exporting table: {table}")
            conn.execute(f"CREATE OR REPLACE TABLE pg.gold.{table} AS SELECT * FROM {table}")
            
        logger.info("Data export completed successfully.")
        
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    export_gold_to_postgres()
