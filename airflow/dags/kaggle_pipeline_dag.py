from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'hamza',
    'depends_on_past': False,
    'start_date': datetime(2026, 4, 23),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'kaggle_ingestion_pipeline',
    default_args=default_args,
    description='Pipeline d\'ingestion directe via l\'API Kaggle (Demande Encadrant)',
    schedule_interval=None, 
    catchup=False,
    tags=['pfe', 'kaggle', 'bronze'],
) as dag:

    # 1. Ingestion Kaggle -> Bronze
    # Note : Le chemin /opt/airflow correspond au montage de volume dans Docker
    ingest_kaggle = BashOperator(
        task_id='ingest_kaggle_to_bronze',
        bash_command='python /opt/airflow/src/ingestion/kaggle_ingestor.py',
    )

    # 2. Transformation Silver (dbt)
    dbt_run = BashOperator(
        task_id='dbt_run_silver',
        bash_command='cd /opt/airflow/dbt && dbt run --select silver --log-path /tmp/dbt_logs',
    )

    # 3. Tests de Qualité (dbt)
    dbt_test = BashOperator(
        task_id='dbt_test_silver',
        bash_command='cd /opt/airflow/dbt && dbt test --select silver --log-path /tmp/dbt_logs',
    )

    # 4. Rapport de Qualité (Persistance dans PostgreSQL pour Grafana)
    generate_report = BashOperator(
        task_id='generate_dq_report',
        bash_command='python /opt/airflow/src/quality/dq_reporter.py',
    )

    # Ordonnancement linéaire
    ingest_kaggle >> dbt_run >> dbt_test >> generate_report
