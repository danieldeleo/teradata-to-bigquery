# dag_triggerer.py
# This is the DAG that triggers the other DAG.

from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.utils.dates import days_ago
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

# Define the controller DAG
with DAG(
    dag_id="dag_triggerer",
    start_date=days_ago(1),
        schedule=None,
        catchup=False,
        max_active_runs=1,
        default_args={
            "retries": 0
        }
) as dag:
    # Task to trigger the target DAG
    # The `trigger_dag_id` must match the `dag_id` of the DAG you want to run.
    trigger_target_dag = TriggerDagRunOperator(
        task_id="trigger_target_dag_task",
        trigger_dag_id="circular_conf_achilles_heel",  # This is the ID of the DAG to be triggered
        wait_for_completion=False, # Set to True if you want the controller to wait for the target to finish
        # You can pass configuration to the triggered DAG like this:
        conf={"steps":[{"name":"middle", "type":"middle", "params":{"steps":{}}}]},
    )
