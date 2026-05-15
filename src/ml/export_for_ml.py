import duckdb
import os
import pandas as pd
from dotenv import load_dotenv

def export_ml_data():
    load_dotenv()
    
    # Chemins
    db_path = os.getenv("DUCKDB_DATABASE_PATH", "data/processed/warehouse.duckdb")
    output_path = "data/ml_features.csv"
    
    print(f"INFO: Connexion a DuckDB : {db_path}")
    con = duckdb.connect(database=db_path, read_only=True)
    
    query = """
        SELECT * 
        FROM main.mart_ml_prediction_master 
        WHERE delivery_days IS NOT NULL
    """
    
    print("INFO: Extraction des donnees...")
    df = con.execute(query).df()
    
    # Créer le dossier data s'il n'existe pas
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Sauvegarde
    df.to_csv(output_path, index=False)
    print(f"SUCCESS: Export reussi ! {len(df)} lignes sauvegardees dans {output_path}")
    
    con.close()

if __name__ == "__main__":
    export_ml_data()
