import os
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

DUCKDB_PATH = os.getenv('DUCKDB_DATABASE_PATH', 'data/processed/warehouse.duckdb')

def export_to_postgres(df, table_name, host, port, user, password, db):
    """Exporte un DataFrame vers une instance PostgreSQL spécifique."""
    try:
        # Encodage du mot de passe pour gérer les caractères spéciaux comme '@'
        safe_password = quote_plus(password)
        conn_str = f"postgresql://{user}:{safe_password}@{host}:{port}/{db}"
        db_engine = create_engine(conn_str)
        
        # On utilise le schéma 'gold' pour l'organisation
        with db_engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS gold;"))
            conn.commit()
            
        df.to_sql(
            table_name, 
            db_engine, 
            schema='gold', 
            if_exists='replace', 
            index=False
        )
        logger.info(f"Successfully exported {table_name} to {host}")
    except Exception as e:
        logger.error(f"Error exporting {table_name} to {host}: {e}")

def export_gold_to_postgres():
    """
    Exports Gold layer tables from DuckDB to PostgreSQL (Local + Cloud).
    """
    try:
        # 1. Connexion DuckDB
        logger.info(f"Connecting to DuckDB: {DUCKDB_PATH}")
        duck_conn = duckdb.connect(DUCKDB_PATH)
        
        gold_tables = [
            'dim_date', 'dim_products', 'dim_customers', 'dim_sellers',
            'fct_orders', 'fct_order_items', 'fct_order_reviews',
            'mart_ml_prediction_master', 'mart_customer_scoring',
            'vw_sales_performance', 'vw_logistics_sla', 
            'vw_customer_sentiment', 'vw_customer_risk_360'
        ]
        
        for table in gold_tables:
            logger.info(f"Processing table: {table}")
            df = duck_conn.execute(f"SELECT * FROM {table}").df()
            
            # --- EXPORT 1: LOCAL POSTGRES (DOCKER) ---
            export_to_postgres(
                df, table,
                os.getenv('POSTGRES_DWH_HOST', 'localhost'),
                os.getenv('POSTGRES_DWH_PORT', '5433'),
                os.getenv('POSTGRES_DWH_USER', 'admin'),
                os.getenv('POSTGRES_DWH_PASSWORD', 'admin'),
                os.getenv('POSTGRES_DWH_DB', 'dwh_db')
            )
            
            # --- EXPORT 2: SUPABASE CLOUD (IF CONFIGURED) ---
            supa_host = os.getenv('SUPABASE_HOST')
            if supa_host:
                logger.info(f"Syncing {table} to Supabase Cloud...")
                export_to_postgres(
                    df, table,
                    supa_host,
                    os.getenv('SUPABASE_PORT', '6543'),
                    os.getenv('SUPABASE_USER'),
                    os.getenv('SUPABASE_PASSWORD'),
                    os.getenv('SUPABASE_DB', 'postgres')
                )
        
        logger.info("Data export (Local + Cloud) completed successfully.")
        
    except Exception as e:
        logger.error(f"Critical error during export: {e}")
    finally:
        if 'duck_conn' in locals():
            duck_conn.close()

if __name__ == "__main__":
    export_gold_to_postgres()
