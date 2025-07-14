# Import necessary libraries
from __future__ import annotations

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from airflow.operators.empty import EmptyOperator


# Define the DAG
@dag(
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    description="Example of a DAG which can cause Airflow Scheduler to endlessly restart itself, rendering Composer inoperable.",
)
def circular_conf_achilles_heel():
    # Start task (optional, good practice)
    start = EmptyOperator(task_id="start")

    @task
    def create_circular_conf(**context):
        params = {'some_key': {}}
        params['some_key']['another_key'] = params['some_key']

    # End task (optional, good practice)
    end = EmptyOperator(task_id="end")

    # Define task dependencies
    end(circular_conf_achilles_heel(start))

circular_conf_achilles_heel()