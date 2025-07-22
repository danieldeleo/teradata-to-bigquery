from __future__ import annotations


from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from airflow.decorators import task, task_group
from airflow.providers.google.cloud.sensors.cloud_composer import CloudComposerDAGRunSensor
from airflow.utils.dates import days_ago
from time import sleep


# --- CONFIGURATION ---
# TODO: Replace with your GCP Project ID, Composer Environment Region, and Composer Environment Name
GCP_PROJECT_ID = "danny-bq"
COMPOSER_REGION = "us-central1"  # e.g., us-central1
COMPOSER_ENVIRONMENT_NAME = "small"

# The dag_id of the DAG you want to wait for.
# This example waits for the `gcs_object_existence_sensor_test` DAG.
TARGET_DAG_ID = "dag_triggerer"
# --- END CONFIGURATION ---

with DAG(
    dag_id="composer_dag_sensor_example_dynamic",
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    description="A DAG that demonstrates the use of CloudComposerDagSensor.",
) as dag:
    @task
    def get_num_sleepy_tasks():
        seconds_of_sleep = 5
        return [seconds_of_sleep] * 1500
    
    @task_group
    def sleepy_task_group(seconds_of_sleep):
        sensor = CloudComposerDAGRunSensor(
            task_id="wait_for_another_dag",
            project_id=GCP_PROJECT_ID,
            region=COMPOSER_REGION,
            environment_id=COMPOSER_ENVIRONMENT_NAME,
            composer_dag_id=TARGET_DAG_ID,
            # deferrable=True,
        )
        @task
        def sleepy_task_1(seconds_of_sleep):
            sleep(seconds_of_sleep)
            return seconds_of_sleep
        @task
        def sleepy_task_2(seconds_of_sleep):
            sleep(seconds_of_sleep)
            return seconds_of_sleep
        @task
        def sleepy_task_3(seconds_of_sleep):
            sleep(seconds_of_sleep)
            return seconds_of_sleep
        
        sleepy_task_3(sleepy_task_2(sensor >> sleepy_task_1(seconds_of_sleep)))
    sleepy_task_group.expand(seconds_of_sleep=get_num_sleepy_tasks())
    
