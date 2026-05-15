import os
import json
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Seuil d'alerte par défaut (peut être configuré via .env)
ALERT_THRESHOLD = float(os.getenv("DQ_ALERT_THRESHOLD", 90.0))

def report_dq_score():
    # 1. Lire les résultats de dbt (Recherche intelligente du fichier)
    cwd = os.getcwd()
    print(f"DEBUG: Current Working Directory: {cwd}")
    
    possible_paths = [
        os.getenv("DBT_TARGET_PATH", "dbt/target/run_results.json"),
        "dbt/target/run_results.json",
        "/opt/airflow/dbt/target/run_results.json",
        "../dbt/target/run_results.json"
    ]
    
    run_results_path = None
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        print(f"DEBUG: Checking path: {abs_path}")
        if os.path.exists(abs_path):
            run_results_path = abs_path
            print(f"SUCCESS: Found run_results.json at: {run_results_path}")
            break
            
    if not run_results_path:
        error_msg = f"CRITICAL: Impossible de trouver run_results.json. Chemins testés: {possible_paths}"
        print(f"ERROR: {error_msg}")
        raise FileNotFoundError(error_msg)

    print(f"INFO: Reading dbt results from: {run_results_path}")
    with open(run_results_path, "r") as f:
        run_results = json.load(f)

    # 2. Analyser les succès/échecs et grouper par domaine
    results = run_results.get("results", [])
    total_tests = len(results)
    pass_count = sum(1 for r in results if r.get("status") == "pass")
    fail_count = total_tests - pass_count
    
    quality_score = (pass_count / total_tests * 100) if total_tests > 0 else 0
    batch_id = run_results.get("metadata", {}).get("invocation_id")
    timestamp = datetime.now(timezone.utc).isoformat()

    # Logique de regroupement par domaine (ex: stg_orders)
    domain_stats = {}
    for r in results:
        test_id = r.get("unique_id", "")
        parts = test_id.split(".")
        model_part = parts[-2] if len(parts) > 2 else "unknown"
        
        domain = "unknown"
        for potential in ["stg_orders", "stg_customers", "stg_products", "stg_order_items", 
                          "stg_order_payments", "stg_order_reviews", "stg_sellers", 
                          "stg_geolocation", "stg_category_translation",
                          "dim_customers", "dim_products", "dim_sellers", "dim_date",
                          "fct_orders", "fct_order_items", "fct_order_reviews",
                          "mart_ml_prediction_master", "mart_customer_scoring",
                          "vw_sales_performance", "vw_logistics_sla", 
                          "vw_customer_sentiment", "vw_customer_risk_360"]:
            if potential in model_part:
                domain = potential
                break
        
        if domain not in domain_stats:
            domain_stats[domain] = {"total": 0, "passed": 0}
        
        domain_stats[domain]["total"] += 1
        if r.get("status") == "pass":
            domain_stats[domain]["passed"] += 1

    # 3. Calcul de la tendance (Comparaison avec le dernier rapport)
    base_dir = "/opt/airflow" if os.path.exists("/opt/airflow") else "."
    report_dir = os.path.join(base_dir, "data", "processed", "dq_reports")
    os.makedirs(report_dir, exist_ok=True)

    previous_score = None
    trend_str = ""
    try:
        # Lister les fichiers JSON triés par date (du plus récent au plus ancien)
        existing_reports = [f for f in os.listdir(report_dir) if f.startswith("dq_report_") and f.endswith(".json")]
        existing_reports.sort(reverse=True)
        
        if existing_reports:
            with open(os.path.join(report_dir, existing_reports[0]), "r") as f:
                prev_data = json.load(f)
                previous_score = prev_data.get("quality_score")
                
            if previous_score is not None:
                diff = quality_score - previous_score
                if diff > 0:
                    trend_str = f"(↑ +{diff:.2f}% vs previous)"
                elif diff < 0:
                    trend_str = f"(↓ {diff:.2f}% vs previous)"
                else:
                    trend_str = "(→ stable)"
    except Exception as e:
        print(f"DEBUG: Erreur calcul tendance : {e}")

    print(f"DQ Score : {quality_score:.2f}% {trend_str} ({pass_count}/{total_tests} tests passés)")

    # 4. Générer un rapport JSON structuré
    report = {
        "timestamp": timestamp,
        "batch_id": batch_id,
        "quality_score": round(quality_score, 2),
        "previous_score": previous_score,
        "summary": {
            "total_tests": total_tests,
            "passed": pass_count,
            "failed": fail_count
        },
        "domain_breakdown": domain_stats,
        "details": [
            {
                "test_id": r.get("unique_id"),
                "status": r.get("status"),
                "message": r.get("message"),
                "execution_time": r.get("execution_time")
            } for r in results
        ]
    }

    # 4. Sauvegarder le rapport JSON (pour l'historique et la tendance futur)
    report_file = os.path.join(report_dir, f"dq_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=4)
    print(f"INFO: Rapport JSON généré : {report_file}")

    # 5. Générer le rapport Markdown (Artifact visuel)
    md_file = os.path.join(report_dir, "dq_report_latest.md")
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# Rapport de Qualite des Donnees (DQ Artifact)\n\n")
        f.write(f"**Date d'execution** : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Batch ID** : `{batch_id}`\n\n")
        
        # Indicateur visuel du score et de la tendance
        status_label = "SUCCESS" if quality_score >= ALERT_THRESHOLD else "CRITICAL"
        f.write(f"## Resume Global [{status_label}]\n")
        f.write(f"> **Score de Qualite : {quality_score:.2f}%** {trend_str}\n\n")
        f.write(f"> *Seuil d'alerte : {ALERT_THRESHOLD}%*\n\n")
        
        f.write(f"| Metrique | Valeur |\n")
        f.write(f"| :--- | :--- |\n")
        f.write(f"| Total des tests | {total_tests} |\n")
        f.write(f"| Tests reussis | {pass_count} |\n")
        f.write(f"| Tests echoues | {fail_count} |\n\n")
        
        # Ajout de la répartition par domaine
        f.write(f"## Repartition par Domaine\n")
        f.write(f"| Domaine | Tests | Succes | Score |\n")
        f.write(f"| :--- | :---: | :---: | :---: |\n")
        for domain, stats in domain_stats.items():
            score = (stats["passed"] / stats["total"] * 100)
            indicator = "[PASS]" if score == 100 else "[WARN]" if score >= ALERT_THRESHOLD else "[FAIL]"
            f.write(f"| {domain} | {stats['total']} | {stats['passed']} | {indicator} {score:.1f}% |\n")
        f.write("\n")
        
        if fail_count > 0:
            f.write(f"### Details des Echecs\n")
            f.write(f"| Test ID | Message d'erreur |\n")
            f.write(f"| :--- | :--- |\n")
            for r in results:
                if r.get("status") != "pass":
                    msg = r.get("message", "N/A").replace("\n", " ")
                    f.write(f"| `{r.get('unique_id')}` | {msg} |\n")
            f.write("\n")
        else:
            f.write(f"### Aucun echec detecte.\n\n")

    print(f"INFO: Artifact Markdown généré : {md_file}")

    # 5. Sauvegarder dans PostgreSQL (Métriques détaillées pour Grafana)
    try:
        # Détection intelligente de l'hôte (Docker vs Local)
        # Si on est dans Docker, 'postgres_dwh' est résoluble, sinon on utilise 127.0.0.1
        host = os.getenv("POSTGRES_DWH_HOST", "127.0.0.1")
        port = os.getenv("POSTGRES_DWH_PORT", "5433")
        
        # En mode Docker Airflow, le port est généralement 5432
        if host == "postgres_dwh":
            port = "5432"

        # 5a. Connexion aux deux bases (DuckDB pour la lecture, Postgres pour le stockage)
        import duckdb
        
        possible_duck_paths = [
            os.getenv("DUCKDB_DATABASE_PATH", "data/processed/warehouse.duckdb"),
            "data/processed/warehouse.duckdb",
            "/opt/airflow/data/processed/warehouse.duckdb",
            "../data/processed/warehouse.duckdb"
        ]
        
        duck_path = None
        for p in possible_duck_paths:
            if os.path.exists(p):
                duck_path = p
                break
        
        if not duck_path:
            print(f"WARNING: DuckDB introuvable à {possible_duck_paths}. Les volumes ne seront pas mis à jour.")
            duck_conn = None
        else:
            print(f"INFO: Calcul des volumes depuis {duck_path}")
            duck_conn = duckdb.connect(database=duck_path, read_only=True)
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=os.getenv("POSTGRES_DWH_USER"),
            password=os.getenv("POSTGRES_DWH_PASSWORD"),
            dbname=os.getenv("POSTGRES_DWH_DB")
        )
        with conn.cursor() as cur:
            # Migration : Renommer timestamp en run_at si nécessaire
            cur.execute("""
                DO $$ 
                BEGIN 
                    IF EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema='quality' AND table_name='dq_metrics' AND column_name='timestamp') THEN
                        ALTER TABLE quality.dq_metrics RENAME COLUMN timestamp TO run_at;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema='quality' AND table_name='dq_domain_metrics' AND column_name='timestamp') THEN
                        ALTER TABLE quality.dq_domain_metrics RENAME COLUMN timestamp TO run_at;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_schema='quality' AND table_name='volume_metrics' AND column_name='timestamp') THEN
                        ALTER TABLE quality.volume_metrics RENAME COLUMN timestamp TO run_at;
                    END IF;
                END $$;
            """)
            cur.execute("""
                CREATE SCHEMA IF NOT EXISTS quality;
                CREATE TABLE IF NOT EXISTS quality.dq_metrics (
                    id SERIAL PRIMARY KEY, run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pass_count INT, fail_count INT, total_tests INT, quality_score FLOAT, batch_id TEXT
                );
                CREATE TABLE IF NOT EXISTS quality.dq_domain_metrics (
                    id SERIAL PRIMARY KEY, run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    domain_name TEXT, pass_count INT, fail_count INT, total_tests INT, quality_score FLOAT, batch_id TEXT
                );
                CREATE TABLE IF NOT EXISTS quality.volume_metrics (
                    id SERIAL PRIMARY KEY, run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    schema_name TEXT, table_name TEXT, row_count INT, batch_id TEXT
                );
            """)

            # 5b. Insertion du score Global
            cur.execute("""
                INSERT INTO quality.dq_metrics (pass_count, fail_count, total_tests, quality_score, batch_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (pass_count, fail_count, total_tests, quality_score, batch_id))

            # 5c. Insertion des scores par Domaine (stg_orders, stg_customers, etc.)
            for domain, stats in domain_stats.items():
                domain_score = (stats["passed"] / stats["total"] * 100)
                cur.execute("""
                    INSERT INTO quality.dq_domain_metrics (domain_name, pass_count, fail_count, total_tests, quality_score, batch_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (domain, stats["passed"], stats["total"] - stats["passed"], stats["total"], domain_score, batch_id))

            # 5d. Capture des Volumes (Row Counts) pour le monitoring des flux
            tables_to_monitor = [
                ("bronze", "orders"), ("bronze", "customers"), ("bronze", "products"),
                ("silver", "stg_orders"), ("silver", "stg_customers"), ("silver", "stg_products"),
                ("gold", "dim_customers"), ("gold", "dim_products"), ("gold", "fct_orders"),
                ("gold", "mart_ml_prediction_master"), ("gold", "mart_customer_scoring")
            ]
            if duck_conn:
                for schema, table in tables_to_monitor:
                    try:
                        # On compte dans DuckDB
                        row_count = duck_conn.execute(f"SELECT COUNT(*) FROM {schema}.{table}").fetchone()[0]
                        # On insère dans Postgres
                        cur.execute("""
                            INSERT INTO quality.volume_metrics (schema_name, table_name, row_count, batch_id)
                            VALUES (%s, %s, %s, %s)
                        """, (schema, table, row_count, batch_id))
                    except Exception as e:
                        print(f"DEBUG: Skipping volume check for {schema}.{table}: {e}")
                        continue
                duck_conn.close()
            else:
                print("WARNING: Skipping volume checks as DuckDB is not connected.")

            conn.commit()
            print("SUCCESS: Métriques détaillées (DQ + Volumes) insérées dans PostgreSQL")
        conn.close()
    except Exception as e:
        print(f"ERROR: Erreur lors de l'insertion PostgreSQL : {e}")
        raise e  # Fail the task if DB insertion fails

    # 5. Vérifier le seuil d'alerte (Fail-Fast)
    if quality_score < ALERT_THRESHOLD:
        error_msg = f"CRITICAL: DQ Score {quality_score:.2f}% est inférieur au seuil {ALERT_THRESHOLD}% !"
        print(f"CRITICAL: {error_msg}")
        # En environnement Airflow, lever une exception pour marquer la tâche en échec
        raise RuntimeError(error_msg)

if __name__ == "__main__":
    report_dq_score()
