from __future__ import annotations

import pendulum
from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

# Assuming custom_external_task_sensor.py is in the dags folder
from custom_external_task_sensor import CustomExternalTaskSensor

TARGET_DAG_ID = "custom_sleepy_task_group_example"
# This is a mapped task, so we can demonstrate waiting for a specific map_index
TARGET_TASK_ID = "sleepy_task_group.my_custom_sleepy_task_group_1.sleep_for"

with DAG(
    dag_id="custom_external_task_sensor_example",
    start_date=pendulum.datetime(2025, 4, 21, tz="America/New_York"),
    schedule=None,
    catchup=False,
    tags=["sensor", "example"],
) as dag:
    start = EmptyOperator(task_id="start")

    trigger_target_dag = TriggerDagRunOperator(
        task_id="trigger_target_dag",
        trigger_dag_id=TARGET_DAG_ID,
        wait_for_completion=False,
        # The run_id will be available in XComs.
        # We pass some params to the target DAG.
        conf={"seconds_to_sleep": 60, "number_of_sleepy_tasks": 3},
    )

    # Example of waiting for a specific mapped task instance using dag_run_id
    wait_for_mapped_task_instance = CustomExternalTaskSensor(
        task_id="wait_for_mapped_task_instance",
        external_dag_id=TARGET_DAG_ID,
        external_dag_run_id="{{ ti.xcom_pull(task_ids='trigger_target_dag').run_id }}",
        external_task_id=TARGET_TASK_ID,
        external_task_map_index=1,  # Wait for the second mapped instance (index starts at 0)
        poke_interval=10,
        timeout=600,
    )

    # Example of waiting for the entire mapped task to complete
    wait_for_entire_mapped_task = CustomExternalTaskSensor(
        task_id="wait_for_entire_mapped_task",
        external_dag_id=TARGET_DAG_ID,
        external_dag_run_id="{{ ti.xcom_pull(task_ids='trigger_target_dag').run_id }}",
        external_task_id=TARGET_TASK_ID,
        poke_interval=10,
        timeout=600,
    )

    # Example of waiting for a task to succeed within a specific date range.
    # This is useful when you don't know the exact run_id but know it should have run
    # sometime in the last hour.
    wait_for_task_in_date_range = CustomExternalTaskSensor(
        task_id="wait_for_task_in_date_range",
        external_dag_id=TARGET_DAG_ID,
        external_task_id=TARGET_TASK_ID,
        execution_date_start="{{ (data_interval_end - macros.timedelta(hours=1)).isoformat() }}",
        execution_date_end="{{ data_interval_end.isoformat() }}",
        poke_interval=10,
        timeout=600,
    )

    all_done = EmptyOperator(task_id="all_done")

    (
        start
        >> trigger_target_dag
        >> [
            wait_for_mapped_task_instance,
            wait_for_entire_mapped_task,
            wait_for_task_in_date_range,
        ]
        >> all_done
    )
