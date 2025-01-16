# olist_etl_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from Chapter06.etl_functions import extract, transform, load_to_database

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 7, 25),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'olist_etl_pipeline',
    default_args=default_args,
    description='ETL pipeline for Olist dataset',
    schedule=timedelta(days=1),
)

with dag:
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract,
    )

    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform,
    )

    load_task = PythonOperator(
        task_id='load_data',
        python_callable=load_to_database,
        op_kwargs={
            'processed_data_dir': '{{ task_instance.xcom_pull(task_ids="transform_data") }}',
            'db_name': 'olist.db',
        },
    )
    
    extract_task >> transform_task >> load_task
