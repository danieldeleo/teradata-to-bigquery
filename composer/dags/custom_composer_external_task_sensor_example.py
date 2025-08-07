from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator

from custom_composer_external_task_sensor import CloudComposerExternalTaskSensor

# --- CONFIGURATION ---
# TODO: Replace with your GCP Project ID, Composer Environment Region, and Composer Environment Name
GCP_PROJECT_ID = "your-gcp-project-id"
COMPOSER_REGION = "us-central1"
COMPOSER_ENVIRONMENT_NAME = "your-composer-environment-name"

# The dag_id and task_id of the DAG you want to wait for.
TARGET_DAG_ID = "gcs_object_existence_sensor_test"
TARGET_TASK_ID = "delete_trigger_file"
# --- END CONFIGURATION ---

with DAG(
    dag_id="custom_composer_external_task_sensor_example",
    start_date=pendulum.datetime(2025, 4, 21, tz="America/New_York"),
    schedule=None,
    catchup=False,
    tags=["composer", "sensor", "example"],
) as dag:
    start = EmptyOperator(task_id="start")

    wait_for_task = CloudComposerExternalTaskSensor(
        task_id="wait_for_external_task",
        project_id=GCP_PROJECT_ID,
        region=COMPOSER_REGION,
        environment_id=COMPOSER_ENVIRONMENT_NAME,
        external_dag_id=TARGET_DAG_ID,
        external_task_id=TARGET_TASK_ID,
        deferrable=True,
        poke_interval=30,
    )

    all_done = EmptyOperator(task_id="all_done")

    start >> wait_for_task >> all_done
