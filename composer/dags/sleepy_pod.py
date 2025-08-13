"""Example of a Composer DAG that runs a long-running (5min) KubernetesPodOperator with retries."""

import datetime

import airflow
from airflow.decorators import dag
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator


@dag(
    schedule_interval=None,
    start_date=airflow.utils.dates.days_ago(1),
    default_args={
        "retries": 10,
        "retry_delay": datetime.timedelta(seconds=10),
    },
)
def sleepy_pod():
    KubernetesPodOperator(
        task_id="sleep",
        cmds=["bash"],
        arguments=[
            "-c",
            r"""
            set -e && \
            echo "Try number: $AIRFLOW_RETRY_NUMBER" && \
            echo "Sleeping for 5 minutes" && \
            sleep 5m
            """,
        ],
        env_vars={"AIRFLOW_RETRY_NUMBER": "{{ task_instance.try_number }}"},
        image="gcr.io/google.com/cloudsdktool/cloud-sdk:latest",
        namespace="composer-user-workloads",
    )


sleepy_pod()
