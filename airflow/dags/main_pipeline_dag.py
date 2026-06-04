from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

# Import des sensors personnalisés
from sensors.source_sensor import PostgresHealthSensor, APIHealthSensor

def on_failure_callback(context):
    """Log l'échec dans les logs et pourrait envoyer une alerte."""
    task_id = context.get('task_instance').task_id
    err = context.get('exception')
    logging.error(f"Tâche {task_id} échouée ! Erreur : {err}")

def on_success_callback(context):
    """Log le succès."""
    task_id = context.get('task_instance').task_id
    logging.info(f"Tâche {task_id} terminée avec succès.")

# Configuration des arguments par défaut
default_args = {
    'owner': 'Hamza',
    'depends_on_past': False,
    'start_date': datetime(2026, 4, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'on_failure_callback': on_failure_callback,
}

with DAG(
    'e-commerce_platform_industrialized',
    default_args=default_args,
    description='Pipeline Industriel : Health Checks -> Ingestion -> dbt -> DQ Report',
    schedule_interval='@daily',
    catchup=False,
    tags=['pfe', 'industrial', 'quality'],
) as dag:

    # 1. Health Checks (Sécurité)
    check_db_source = PostgresHealthSensor(
        task_id='check_postgres_source',
        conn_id_env_prefix='POSTGRES_SOURCE',
        poke_interval=30,
        timeout=120
    )

    check_api_source = APIHealthSensor(
        task_id='check_api_source',
        url='http://fastapi_mock:80',
        poke_interval=30,
        timeout=120
    )

    # 2. Détection de Drift
    check_drift = BashOperator(
        task_id='check_source_drift',
        bash_command='export PYTHONPATH=/opt/airflow && python -m src.quality.drift_detector',
    )

    # 3. Ingestion des sources
    ingest_csv = BashOperator(
        task_id='ingest_csv_to_bronze',
        bash_command='export PYTHONPATH=/opt/airflow && python -m src.ingestion.pipeline_csv_to_bronze',
    )

    ingest_db = BashOperator(
        task_id='ingest_db_to_bronze',
        bash_command='export PYTHONPATH=/opt/airflow && python -m src.ingestion.pipeline_db_to_bronze',
    )

    ingest_api = BashOperator(
        task_id='ingest_api_to_bronze',
        bash_command='export PYTHONPATH=/opt/airflow && python -m src.ingestion.pipeline_api_to_bronze',
    )

    # 4. Transformation Silver (dbt)
    dbt_run_silver = BashOperator(
        task_id='dbt_run_silver',
        bash_command='cd /opt/airflow/dbt && dbt deps --log-path /tmp/dbt_logs && dbt --log-path /tmp/dbt_logs run --select silver',
        on_success_callback=on_success_callback
    )

    # 5. Tests de Qualité & Rapport Silver
    dbt_test_silver = BashOperator(
        task_id='dbt_test_silver',
        bash_command='cd /opt/airflow/dbt && dbt --log-path /tmp/dbt_logs test --select silver',
    )

    dq_report_silver = BashOperator(
        task_id='generate_dq_report_silver',
        bash_command='cd /opt/airflow && export PYTHONPATH=/opt/airflow && export DQ_LAYER=silver && python -m src.quality.dq_reporter',
        on_success_callback=on_success_callback
    )

    # 6. Transformation Gold (dbt)
    dbt_run_gold = BashOperator(
        task_id='dbt_run_gold',
        bash_command='cd /opt/airflow/dbt && dbt deps --quiet && dbt --log-path /tmp/dbt_logs run --select gold',
        on_success_callback=on_success_callback
    )

    # 7. Tests de Qualité & Rapport Gold
    dbt_test_gold = BashOperator(
        task_id='dbt_test_gold',
        bash_command='cd /opt/airflow/dbt && dbt --log-path /tmp/dbt_logs test --select gold',
    )

    dq_report_gold = BashOperator(
        task_id='generate_dq_report_gold',
        bash_command='cd /opt/airflow && export PYTHONPATH=/opt/airflow && export DQ_LAYER=gold && python -m src.quality.dq_reporter',
        on_success_callback=on_success_callback
    )

    # 8. Synchronisation vers le DWH (PostgreSQL)
    sync_gold = BashOperator(
        task_id='sync_gold_to_postgres',
        bash_command='export PYTHONPATH=/opt/airflow && python -m src.processing.gold_exporter',
        on_success_callback=on_success_callback
    )

    # 9. Batch Scoring ML (M1 -> M2 -> Règle segmentation -> quality.ml_predictions)
    batch_scoring = BashOperator(
        task_id='batch_scoring',
        bash_command='cd /opt/airflow && export PYTHONPATH=/opt/airflow && python -m src.ml.scoring_pipeline',
        on_success_callback=on_success_callback
    )

    # Définition des dépendances
    [check_db_source, check_api_source] >> check_drift
    check_drift >> [ingest_csv, ingest_db, ingest_api]
    [ingest_csv, ingest_db, ingest_api] >> dbt_run_silver >> dbt_test_silver >> dq_report_silver
    dq_report_silver >> dbt_run_gold >> dbt_test_gold >> dq_report_gold >> sync_gold >> batch_scoring
