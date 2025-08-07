from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from custom_composer_external_task_sensor import CloudComposerExternalTaskSensor

# --- CONFIGURATION ---
# TODO: Replace with your GCP Project ID, Composer Environment Region, and Composer Environment Name
GCP_PROJECT_ID = "danny-bq"
COMPOSER_REGION = "us-east4"
COMPOSER_ENVIRONMENT_NAME = "east"

# The dag_id and task_id of the DAG you want to wait for.
TARGET_DAG_ID = "custom_sleepy_task_group_example"
TARGET_TASK_ID = "sleepy_task_group.my_custom_sleepy_task_group_1.sleep_for"
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
        external_dag_run_id="manual__2025-08-07T16:02:11+00:00",
        external_task_id=TARGET_TASK_ID,
        # external_task_map_index=7,  # Example of waiting for the first mapped task instance
        # deferrable=True,
        poke_interval=5,
    )

    all_done = EmptyOperator(task_id="all_done")

    start >> wait_for_task >> all_done
