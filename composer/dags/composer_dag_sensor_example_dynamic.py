from __future__ import annotations

from datetime import datetime, timedelta
from time import sleep
from typing import TYPE_CHECKING

from airflow.decorators import task, task_group
from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.google.cloud.sensors.cloud_composer import (
    CloudComposerDAGRunSensor,
)
from airflow.providers.google.cloud.triggers.cloud_composer import (
    CloudComposerDAGRunTrigger,
)
from airflow.utils.dates import days_ago
from dateutil import parser

if TYPE_CHECKING:
    from airflow.utils.context import Context

from airflow.providers.google.common.consts import GOOGLE_DEFAULT_DEFERRABLE_METHOD_NAME

# --- CONFIGURATION ---
# TODO: Replace with your GCP Project ID, Composer Environment Region, and Composer Environment Name
GCP_PROJECT_ID = "danny-bq"
COMPOSER_REGION = "us-central1"  # e.g., us-central1
COMPOSER_ENVIRONMENT_NAME = "small"

# The dag_id of the DAG you want to wait for.
# This example waits for the `gcs_object_existence_sensor_test` DAG.
TARGET_DAG_ID = "dag_triggerer"
# --- END CONFIGURATION ---


class CustomCloudComposerDAGRunTrigger(CloudComposerDAGRunTrigger):
    """This trigger will wait for the DAG run completion even if there's no DAG run."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _check_dag_runs_states(
        self,
        dag_runs: list[dict],
        start_date: datetime,
        end_date: datetime,
    ) -> bool:
        print(f"{dag_runs=}")
        if len(dag_runs) == 0:
            print("No dag runs found")
            return False
        for dag_run in dag_runs:
            if (
                start_date.timestamp()
                < parser.parse(dag_run["logical_date"]).timestamp()
                < end_date.timestamp()
            ) and dag_run["state"] not in self.allowed_states:
                return False
        return True


class CustomComposerDAGRunSensor(CloudComposerDAGRunSensor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_logical_dates(self, context) -> tuple[datetime, datetime]:
        if isinstance(self.execution_range, timedelta):
            if self.execution_range < timedelta(0):
                return context["logical_date"], context[
                    "logical_date"
                ] - self.execution_range
            else:
                return context["logical_date"] - self.execution_range, context[
                    "logical_date"
                ]
        elif isinstance(self.execution_range, list) and len(self.execution_range) > 0:
            return self.execution_range[0], self.execution_range[1] if len(
                self.execution_range
            ) > 1 else context["logical_date"]
        else:
            return context["logical_date"] - timedelta(1), context["logical_date"]

    def execute(self, context: Context) -> None:
        if self.deferrable:
            start_date, end_date = self._get_logical_dates(context)
            self.defer(
                trigger=CustomCloudComposerDAGRunTrigger(
                    project_id=self.project_id,
                    region=self.region,
                    environment_id=self.environment_id,
                    composer_dag_id=self.composer_dag_id,
                    start_date=start_date,
                    end_date=end_date,
                    allowed_states=self.allowed_states,
                    gcp_conn_id=self.gcp_conn_id,
                    impersonation_chain=self.impersonation_chain,
                    poll_interval=self.poll_interval,
                ),
                method_name=GOOGLE_DEFAULT_DEFERRABLE_METHOD_NAME,
            )
        super().super().execute(context)


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
        return [seconds_of_sleep] * 10

    @task_group
    def sleepy_task_group(seconds_of_sleep):
        sensor = CustomComposerDAGRunSensor(
            task_id="wait_for_another_dag",
            project_id=GCP_PROJECT_ID,
            region=COMPOSER_REGION,
            environment_id=COMPOSER_ENVIRONMENT_NAME,
            composer_dag_id=TARGET_DAG_ID,
            poll_interval=60,
            deferrable=True,
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

        # sleepy_task_3(sleepy_task_2(sleepy_task_1(seconds_of_sleep)))
        sleepy_task_3(sleepy_task_2(sensor >> sleepy_task_1(seconds_of_sleep)))

    sleepy_task_group.expand(seconds_of_sleep=get_num_sleepy_tasks())
