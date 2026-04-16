from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Configuration des arguments par défaut
default_args = {
    'owner': 'Hamza',
    'depends_on_past': False,
    'start_date': datetime(2026, 4, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Définition du DAG
with DAG(
    'e-commerce_elt_pipeline',
    default_args=default_args,
    description='Pipeline End-to-End : Ingestion Beam -> Transformation dbt Silver',
    schedule_interval='@daily',
    catchup=False,
    tags=['pfe', 'ingestion', 'dbt'],
) as dag:

    # 0. Détection de Drift (Sécurité Niveau 1)
    check_drift = BashOperator(
        task_id='check_source_drift',
        bash_command='export PYTHONPATH=/opt/airflow && python -m src.quality.drift_detector',
    )

    # 1. Ingestion des sources (en parallèle)
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

    # 2. Transformation Silver (dbt)
    dbt_run_silver = BashOperator(
        task_id='dbt_run_silver',
        bash_command='export DBT_LOG_PATH=/tmp && export DBT_TARGET_PATH=/tmp/target && cd /opt/airflow/dbt && dbt run --select silver',
    )

    # 3. Tests de Qualité (dbt test)
    dbt_test_silver = BashOperator(
        task_id='dbt_test_silver',
        bash_command='export DBT_LOG_PATH=/tmp && export DBT_TARGET_PATH=/tmp/target && cd /opt/airflow/dbt && dbt test --select silver',
    )

    # 4. Rapport de Qualité Final
    dq_report = BashOperator(
        task_id='generate_dq_report',
        bash_command='export PYTHONPATH=/opt/airflow && export DBT_TARGET_PATH=/tmp/target && python -m src.quality.dq_reporter',
    )

    # 5. Définition des dépendances
    check_drift >> [ingest_csv, ingest_db, ingest_api] >> dbt_run_silver >> dbt_test_silver >> dq_report
