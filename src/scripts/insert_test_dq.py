import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def insert_test():
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_DWH_HOST'),
            port=os.getenv('POSTGRES_DWH_PORT'),
            user=os.getenv('POSTGRES_DWH_USER'),
            password=os.getenv('POSTGRES_DWH_PASSWORD'),
            dbname=os.getenv('POSTGRES_DWH_DB')
        )
        cur = conn.cursor()
        cur.execute("INSERT INTO quality.dq_metrics (pass_count, fail_count, total_tests, quality_score, batch_id) VALUES (21, 0, 21, 100.0, 'manual_test_verification');")
        conn.commit()
        print("✅ Ligne de test insérée avec succès dans quality.dq_metrics")
        conn.close()
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    insert_test()
