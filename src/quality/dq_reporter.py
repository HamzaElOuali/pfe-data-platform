import os
import json
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def report_dq_score():
    # 1. Lire les résultats de dbt (chemin par défaut ou via variable d'env)
    target_dir = os.getenv("DBT_TARGET_PATH", os.path.join("dbt", "target"))
    run_results_path = os.path.join(target_dir, "run_results.json")
    
    if not os.path.exists(run_results_path):
        # Fallback pour dbt/target si DBT_TARGET_PATH ne contient rien de concluant
        run_results_path = os.path.join("dbt", "target", "run_results.json")
        if not os.path.exists(run_results_path):
            print(f"⚠️ Fichier {run_results_path} introuvable. Avez-vous lancé 'dbt test' ?")
            return

    with open(run_results_path, "r") as f:
        run_results = json.load(f)

    # 2. Analyser les succès/échecs des tests
    results = run_results.get("results", [])
    total_tests = len(results)
    pass_count = sum(1 for r in results if r.get("status") == "pass")
    fail_count = total_tests - pass_count
    
    quality_score = (pass_count / total_tests * 100) if total_tests > 0 else 0
    batch_id = run_results.get("metadata", {}).get("invocation_id")

    print(f"📊 DQ Score : {quality_score:.2f}% ({pass_count}/{total_tests} tests passés)")

    # 3. Sauvegarder dans PostgreSQL DWH
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_DWH_HOST"),
            port=os.getenv("POSTGRES_DWH_PORT"),
            user=os.getenv("POSTGRES_DWH_USER"),
            password=os.getenv("POSTGRES_DWH_PASSWORD"),
            dbname=os.getenv("POSTGRES_DWH_DB")
        )
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quality.dq_metrics (pass_count, fail_count, total_tests, quality_score, batch_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (pass_count, fail_count, total_tests, quality_score, batch_id))
            conn.commit()
            print("✅ Métriques insérées dans quality.dq_metrics")
        conn.close()
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion PostgreS : {e}")

if __name__ == "__main__":
    report_dq_score()
