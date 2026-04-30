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
        print(f"ERROR: Impossible de trouver run_results.json. Chemins testés: {possible_paths}")
        return

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
                          "stg_geolocation", "stg_category_translation"]:
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
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_DWH_HOST"),
            port=os.getenv("POSTGRES_DWH_PORT"),
            user=os.getenv("POSTGRES_DWH_USER"),
            password=os.getenv("POSTGRES_DWH_PASSWORD"),
            dbname=os.getenv("POSTGRES_DWH_DB")
        )
        with conn.cursor() as cur:
            # 5a. Initialisation des tables de monitoring
            cur.execute("""
                CREATE SCHEMA IF NOT EXISTS quality;
                CREATE TABLE IF NOT EXISTS quality.dq_metrics (
                    id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pass_count INT, fail_count INT, total_tests INT, quality_score FLOAT, batch_id TEXT
                );
                CREATE TABLE IF NOT EXISTS quality.dq_domain_metrics (
                    id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    domain_name TEXT, pass_count INT, fail_count INT, total_tests INT, quality_score FLOAT, batch_id TEXT
                );
                CREATE TABLE IF NOT EXISTS quality.volume_metrics (
                    id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                ("silver", "stg_orders"), ("silver", "stg_customers"), ("silver", "stg_products")
            ]
            for schema, table in tables_to_monitor:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
                    row_count = cur.fetchone()[0]
                    cur.execute("""
                        INSERT INTO quality.volume_metrics (schema_name, table_name, row_count, batch_id)
                        VALUES (%s, %s, %s, %s)
                    """, (schema, table, row_count, batch_id))
                except Exception:
                    conn.rollback() # Si une table n'existe pas encore, on ignore
                    continue

            conn.commit()
            print("SUCCESS: Métriques détaillées (DQ + Volumes) insérées dans PostgreSQL")
        conn.close()
    except Exception as e:
        print(f"ERROR: Erreur lors de l'insertion PostgreSQL : {e}")

    # 5. Vérifier le seuil d'alerte (Fail-Fast)
    if quality_score < ALERT_THRESHOLD:
        error_msg = f"CRITICAL: DQ Score {quality_score:.2f}% est inférieur au seuil {ALERT_THRESHOLD}% !"
        print(f"CRITICAL: {error_msg}")
        # En environnement Airflow, lever une exception pour marquer la tâche en échec
        raise RuntimeError(error_msg)

if __name__ == "__main__":
    report_dq_score()
