"""Example of a Composer DAG that runs a long-running (5min) KubernetesPodOperator with retries."""

import datetime

import airflow
from airflow.decorators import dag, task, task_group
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s


@dag(
    schedule_interval=None,
    start_date=airflow.utils.dates.days_ago(1),
    max_active_tasks=100,
    default_args={
        "retries": 10,
        "retry_delay": datetime.timedelta(seconds=10),
    },
)
def sleepy():
    @task
    def get_sleepy_minutes():
        return [1, 1, 1, 1, 1]

    @task_group
    def sleep_for(minutes):
        @task(multiple_outputs=True)
        def create_kpo_args(minutes):
            arguments = [
                "-c",
                rf"""
                set -e && \
                echo "Try number: $AIRFLOW_RETRY_NUMBER" && \
                echo "Sleeping for {minutes} minutes" && \
                sleep {minutes}m
                """,
            ]
            return {"arguments": arguments}

        kpo_args = create_kpo_args(minutes)
        KubernetesPodOperator(
            task_id="sleepy_pod",
            name="sleepy",
            cmds=["bash"],
            arguments=kpo_args["arguments"],
            env_vars={"AIRFLOW_RETRY_NUMBER": "{{ task_instance.try_number }}"},
            namespace="composer-user-workloads",
            image="teradata/tpt:latest",
            config_file="/home/airflow/composer_kube_config",
            kubernetes_conn_id="kubernetes_default",
            container_resources=k8s.V1ResourceRequirements(
                requests={
                    "cpu": "100m",
                    "memory": "64Mi",
                },
                limits={
                    "cpu": "100m",
                    "memory": "64Mi",
                },
            ),
            # Increase pod startup timeout to 10 minutes
            startup_timeout_seconds=600,
        )

    sleep_for.expand(minutes=get_sleepy_minutes())


# Instantiate the DAG
sleepy()
