"""An example for using Teradata Parallel Transporter (TPT) with Composer."""
import datetime

import airflow
from airflow import models
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.providers.cncf.kubernetes.secret import Secret
from kubernetes.client import models as k8s

TERADATA_HOSTNAME = "10.128.0.26"
TERADATA_USERNAME = "dbc"
SELECT_STATEMENT = "SELECT * FROM tpch.orders;"
GCS_BUCKET = "dannybq"
GCS_PREFIX = "orders"
GCS_OBJECT_NAME = "data.csv"
GCS_MAX_OBJECT_SIZE = "200M"
GCS_CONNECTION_COUNT = "10"
NUM_READ_INSTANCES = 1
NUM_WRITE_INSTANCES = 1

TERADATA_PASSWORD = Secret(
    deploy_type="env",
    deploy_target="TERADATA_PASSWORD",
    secret="tpt-secrets",
    key="TERADATA_PASSWORD",
)

GCS_ACCESS_KEY = Secret(
    deploy_type="env",
    deploy_target="GCS_ACCESS_KEY_ID",
    secret="tpt-secrets",
    key="GCS_ACCESS_KEY_ID",
)

GCS_SECRET_ACCESS_KEY = Secret(
    deploy_type="env",
    deploy_target="GCS_SECRET_ACCESS_KEY",
    secret="tpt-secrets",
    key="GCS_SECRET_ACCESS_KEY",
)


def read_export_tpt():
    with open("/home/airflow/gcs/data/export.tpt", "r") as f:
        return f.read().replace("$", r"\$")


with models.DAG(
    dag_id="tpt",
    schedule_interval=None,
    start_date=airflow.utils.dates.days_ago(1),
    max_active_tasks=2,
) as dag:
    for x in range(10):
        task_id = f"tpt{x}"
        tpt = KubernetesPodOperator(
            task_id=task_id,
            name="tpt",
            cmds=["bash"],
            arguments=[
                "-c",
                rf"""
                set -e && \
                echo "{read_export_tpt()}" > export.tpt && \
                more export.tpt && \
                tbuild -f export.tpt -u "\
                  jobvar_tdpid='{TERADATA_HOSTNAME}', \
                  jobvar_username='{TERADATA_USERNAME}', \
                  jobvar_password='${{TERADATA_PASSWORD}}', \
                  jobvar_num_read_instances={NUM_READ_INSTANCES}, \
                  jobvar_num_write_instances={NUM_WRITE_INSTANCES}, \
                  jobvar_selectstmt='{SELECT_STATEMENT}', \
                  jobvar_accessmoduleinitstr='\
                  Bucket={GCS_BUCKET} \
                  Prefix={GCS_PREFIX}/task_id={task_id}/try_number=${{AIRFLOW_RETRY_NUMBER}}/ \
                  Object={GCS_OBJECT_NAME} \
                  MaxObjectSize={GCS_MAX_OBJECT_SIZE} \
                  ConnectionCount={GCS_CONNECTION_COUNT}'"
                """,
            ],
            env_vars={"AIRFLOW_RETRY_NUMBER": "{{ task_instance.try_number }}"},
            container_resources=k8s.V1ResourceRequirements(
                requests={
                    "cpu": "100m",
                    "memory": "64Mi",
                },
                limits={
                    "cpu": "1000m",
                    "memory": "128Mi",
                },
            ),
            log_events_on_failure=True,
            namespace="composer-user-workloads",
            secrets=[TERADATA_PASSWORD, GCS_ACCESS_KEY, GCS_SECRET_ACCESS_KEY],
            image="teradata/tpt:latest",
            config_file="/home/airflow/composer_kube_config",
            kubernetes_conn_id="kubernetes_default",
        )
