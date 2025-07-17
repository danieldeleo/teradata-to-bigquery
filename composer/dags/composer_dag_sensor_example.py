from __future__ import annotations


from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.google.cloud.sensors.cloud_composer import CloudComposerDAGRunSensor
from airflow.utils.dates import days_ago


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
    dag_id="composer_dag_sensor_example",
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    description="A DAG that demonstrates the use of CloudComposerDagSensor.",
) as dag:
    # This sensor waits for a DAG run to complete in a Cloud Composer environment.
    # It polls the environments.list and environments.get APIs, then checks the Airflow REST API
    # of the target environment for the status of the DAG run.
    wait_for_another_dag = CloudComposerDAGRunSensor(
        task_id="wait_for_another_dag",
        project_id=GCP_PROJECT_ID,
        region=COMPOSER_REGION,
        environment_id=COMPOSER_ENVIRONMENT_NAME,
        composer_dag_id=TARGET_DAG_ID,
        deferrable=True,
    )  

    # An empty operator to run after the sensor succeeds, representing a downstream task.
    all_done = EmptyOperator(task_id="all_done")

    wait_for_another_dag >> all_done