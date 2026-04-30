import os
import pandas as pd
from sqlalchemy import create_engine
# Force Kaggle client to ignore SSL verification
os.environ["KAGGLE_INSECURE"] = "1"
from kaggle.api.kaggle_api_extended import KaggleApi
from dotenv import load_dotenv
import ssl
import requests
import requests
import urllib3

# =================================================================
# BYPASS SSL AGRESSIF (Pour contrer l'interception réseau sur Windows/Docker)
# =================================================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['CURL_CA_BUNDLE'] = ""
os.environ['PYTHONHTTPSVERIFY'] = "0"
# =================================================================

load_dotenv()

# Configuration PostgreSQL DWH
host = os.getenv('POSTGRES_DWH_HOST', 'localhost')
if os.path.exists('/.dockerenv'): # Si on est dans Docker
    host = 'postgres_dwh'

DB_URL = f"postgresql://{os.getenv('POSTGRES_DWH_USER', 'admin')}:{os.getenv('POSTGRES_DWH_PASSWORD', 'admin')}@{host}:{os.getenv('POSTGRES_DWH_PORT', '5432')}/{os.getenv('POSTGRES_DWH_DB', 'dwh_db')}"
engine = create_engine(DB_URL)

# Mapping des fichiers Kaggle vers les tables Bronze
FILE_MAPPING = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_name_translation"
}

def ingest_from_kaggle():
    dataset_id = "olistbr/brazilian-ecommerce"
    download_path = "data/raw/kaggle"
    os.makedirs(download_path, exist_ok=True)

    # 1. Authentification via variables d'environnement (.env)
    try:
        # Les variables KAGGLE_USERNAME et KAGGLE_KEY sont chargées via load_dotenv()
        # Assurez-vous qu'elles sont présentes dans votre fichier .env
        if not os.getenv('KAGGLE_USERNAME') or not os.getenv('KAGGLE_KEY'):
            # Fallback sur KAGGLE_API_TOKEN si KAGGLE_KEY n'est pas défini (cas du .env actuel)
            os.environ['KAGGLE_KEY'] = os.getenv('KAGGLE_API_TOKEN', '')
            
        api = KaggleApi()
        api.authenticate()
        print(f"Connexion Kaggle réussie pour {os.getenv('KAGGLE_USERNAME')}")
        print(f"Telechargement du dataset {dataset_id}...")
        api.dataset_download_files(dataset_id, path=download_path, unzip=True)
    except Exception as e:
        print(f"Tentative de chargement local car l'API a échoué : {e}")

    # 2. Chargement dans PostgreSQL (depuis le dossier local)
    for csv_file, table_name in FILE_MAPPING.items():
        file_path = os.path.join(download_path, csv_file)
        if os.path.exists(file_path):
            print(f"Chargement de {csv_file} vers bronze.{table_name}...")
            try:
                df = pd.read_csv(file_path)
                df['_ingested_at'] = pd.Timestamp.now()
                df['_batch_id'] = f"kaggle_run_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}"
                
                df.to_sql(
                    name=table_name,
                    con=engine,
                    schema="bronze",
                    if_exists="replace", 
                    index=False
                )
                print(f"OK: {table_name} charge ({len(df)} lignes).")
            except Exception as e:
                print(f"Erreur d'insertion pour {table_name} : {e}")
        else:
            print(f"Fichier {csv_file} introuvable à l'emplacement {file_path}")

if __name__ == "__main__":
    ingest_from_kaggle()
