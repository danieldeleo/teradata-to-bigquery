from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from custom_cloud_composer_trigger_dag_run_operator import (
    CloudComposerTriggerDagRunOperator,
)

# --- CONFIGURATION ---
# Replace with your GCP Project ID, Composer Environment Region, and Composer Environment Name
# For the *external* Composer environment where the target DAG resides.
EXTERNAL_GCP_PROJECT_ID = "danny-bq"  # Example: "your-gcp-project"
EXTERNAL_COMPOSER_REGION = "us-east4"  # Example: "us-central1"
EXTERNAL_COMPOSER_ENVIRONMENT_NAME = "east"  # Example: "your-composer-env-name"

# The dag_id of the DAG you want to trigger in the *external* Composer environment.
TARGET_DAG_ID = "custom_sleepy_task_group_example"

# --- END CONFIGURATION ---

with DAG(
    dag_id="custom_cloud_composer_trigger_dag_run_operator_example",
    start_date=pendulum.datetime(2025, 4, 21, tz="America/New_York"),
    schedule=None,
    catchup=False,
    tags=["composer", "trigger", "example"],
    doc_md="""
    ### Cloud Composer Trigger DAG Run Example DAG

    This DAG demonstrates how to use the `CloudComposerTriggerDagRunOperator`
    to trigger a DAG in a *separate* Cloud Composer environment.
    """,
) as dag:
    start = EmptyOperator(task_id="start")

    # Example 1: Trigger a DAG in the external Composer environment
    trigger_external_dag = CloudComposerTriggerDagRunOperator(
        task_id="trigger_external_composer_dag",
        project_id=EXTERNAL_GCP_PROJECT_ID,
        region=EXTERNAL_COMPOSER_REGION,
        environment_id=EXTERNAL_COMPOSER_ENVIRONMENT_NAME,
        trigger_dag_id=TARGET_DAG_ID,
        # wait_for_completion=True, # This would raise an AirflowException
        # Pass some configuration to the triggered DAG
        conf={"seconds_to_sleep": 10, "number_of_sleepy_tasks": 2},
        # Optionally set a specific logical_date for the triggered DAG run
        # logical_date=pendulum.datetime(2025, 8, 1, tz="UTC"),
    )
    end = EmptyOperator(task_id="end")

    start >> trigger_external_dag >> end
