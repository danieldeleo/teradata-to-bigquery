# Import necessary libraries
from __future__ import annotations

from airflow.models.dag import DAG
from airflow.utils.dates import days_ago
from airflow.operators.empty import EmptyOperator
from airflow.operators.python_operator import PythonOperator


# Define the DAG
with DAG(
        dag_id="circular_conf_achilles_heel",
        start_date=days_ago(1),
        schedule=None,
        catchup=False,
        max_active_runs=1,
        description="Example of a DAG which can cause Airflow Scheduler to endlessly restart itself, rendering Composer inoperable.",
    ) as dag:

    # Start task (optional, good practice)
    start = EmptyOperator(task_id="start", dag=dag)

    def _create_circular_conf(**context):
        params = {'some_key': {}}
        params['some_key']['another_key'] = params['some_key']

    create_circular_conf = PythonOperator(task_id="create_circular_conf", python_callable=_create_circular_conf)

    # End task (optional, good practice)
    end = EmptyOperator(task_id="end", dag=dag)

    # Define task dependencies
    start >> create_circular_conf >> end