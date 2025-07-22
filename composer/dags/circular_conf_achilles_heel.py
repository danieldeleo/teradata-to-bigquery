from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

with DAG(
    dag_id="circular_conf_achilles_heel",
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    description="Example of a DAG which can cause Airflow Scheduler to endlessly restart itself, rendering Composer inoperable.",
) as dag:
    start = EmptyOperator(task_id="start")

    def _create_circular_conf(**context):
        context["dag_run"].conf["steps"] = context["dag_run"].conf

    def _downstream_task(**context):
        print("Help!")

    create_circular_conf = PythonOperator(
        task_id="create_circular_conf", python_callable=_create_circular_conf
    )

    downstream_task = PythonOperator(
        task_id="downstream_task", python_callable=_downstream_task
    )

    end = EmptyOperator(task_id="end")

    # Define task dependencies
    start >> create_circular_conf >> downstream_task >> end

    # If you run the create_circular_conf task without a real downstream task
    # (note that the "end" task is an EmptyOperator which doesn't actually get run)
    # then the scheduler doesn't run into infinite sigterm loop.
    # start >> create_circular_conf >> end
