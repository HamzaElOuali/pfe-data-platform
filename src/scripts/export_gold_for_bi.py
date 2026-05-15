import duckdb
import os
import pandas as pd
from dotenv import load_dotenv

def export_gold_tables():
    load_dotenv()
    
    # Configuration
    db_path = os.getenv("DUCKDB_DATABASE_PATH", "data/processed/warehouse.duckdb")
    output_dir = "data/exports_bi"
    
    # Liste des tables et vues de la couche Gold
    tables_to_export = [
        "dim_customers", "dim_sellers", "dim_products", "dim_date",
        "fct_orders", "fct_order_items", "fct_order_reviews",
        "mart_customer_scoring",
        "vw_sales_performance", "vw_logistics_sla", 
        "vw_customer_sentiment", "vw_customer_risk_360"
    ]
    
    if not os.path.exists(db_path):
        print(f"ERROR: La base DuckDB est introuvable : {db_path}")
        return

    print(f"INFO: Connexion a DuckDB : {db_path}")
    con = duckdb.connect(database=db_path, read_only=True)
    
    # Créer le dossier d'export s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"INFO: Debut de l'export vers {output_dir}...")
    
    for table in tables_to_export:
        try:
            print(f"   - Export de {table}...", end=" ", flush=True)
            # On utilise main.{table} car dbt écrit par défaut dans le schema main pour DuckDB
            query = f"SELECT * FROM main.{table}"
            df = con.execute(query).df()
            
            output_file = os.path.join(output_dir, f"{table}.csv")
            df.to_csv(output_file, index=False)
            print(f"OK ({len(df)} lignes)")
        except Exception as e:
            print(f"SKIP (Introuvable ou erreur : {e})")
    
    con.close()
    print(f"\nSUCCESS: Tous les fichiers sont disponibles dans : {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    export_gold_tables()
