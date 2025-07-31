# dag_triggerer.py
# This is the DAG that triggers the other DAG.

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from airflow.models.dag import DAG
from airflow.providers.google.cloud.sensors.cloud_composer import (
    CloudComposerDAGRunSensor,
)
from airflow.utils.dates import days_ago

TARGET_DAG_ID = "sleepy"
# --- CONFIGURATION ---
# TODO: Replace with your GCP Project ID, Composer Environment Region, and Composer Environment Name
GCP_PROJECT_ID = "danny-bq"
COMPOSER_REGION = "us-central1"  # e.g., us-central1
COMPOSER_ENVIRONMENT_NAME = "small"
# Define the controller DAG
with DAG(
    dag_id="dag_triggerer",
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
) as dag:
    # Task to trigger the target DAG
    # The `trigger_dag_id` must match the `dag_id` of the DAG you want to run.
    # trigger_target_dag = TriggerDagRunOperator(
    #     task_id="trigger_target_dag_task",
    #     trigger_dag_id="circular_conf_achilles_heel",  # This is the ID of the DAG to be triggered
    #     wait_for_completion=False, # Set to True if you want the controller to wait for the target to finish
    #     # You can pass configuration to the triggered DAG like this:
    #     conf={"steps":[{"name":"middle", "type":"middle", "params":{"steps":{}}}]},
    # )
    # run_airflow_cli_cmd = CloudComposerRunAirflowCLICommandOperator(
    #     task_id="run_airflow_cli_cmd",
    #     project_id="danny-bq",
    #     environment_id="small",
    #     region="us-central1",
    #     # command="dags trigger -- sleepy",
    #     command=f"dags trigger {TARGET_DAG_ID} --run-id {{{{ ts_nodash }}}}",
    #     gcp_conn_id="google_cloud_default",
    #     # You can run this operator in the deferrable mode:
    #     deferrable=True,
    # )
    sensor = CloudComposerDAGRunSensor(
        task_id="wait_for_another_dag",
        project_id=GCP_PROJECT_ID,
        region=COMPOSER_REGION,
        environment_id=COMPOSER_ENVIRONMENT_NAME,
        composer_dag_id=TARGET_DAG_ID,
        execution_range=[
            datetime.now(ZoneInfo("America/New_York")).replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            datetime.now(ZoneInfo("America/New_York")),
        ],
        # deferrable=True,
    )
    sensor
