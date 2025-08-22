"""
An example DAG that uses KubernetesPodOperator to process a file from GCS.
"""

import pendulum
from airflow.decorators import dag
from airflow.models.param import Param
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

# Define default parameters for the DAG
# It's a good practice to allow these to be overridden at trigger time.
GCS_BUCKET = "your-gcs-bucket-name"  # <--- CHANGE THIS
INPUT_OBJECT = "path/to/your/input_file.txt"  # <--- CHANGE THIS
OUTPUT_OBJECT = "path/to/your/processed_file.txt"  # <--- CHANGE THIS


@dag(
    dag_id="gcs_file_processor",
    schedule=None,
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["gcs", "kubernetes", "example"],
    params={
        "gcs_bucket": Param(GCS_BUCKET, type="string", title="GCS Bucket"),
        "input_object": Param(INPUT_OBJECT, type="string", title="Input GCS Object"),
        "output_object": Param(OUTPUT_OBJECT, type="string", title="Output GCS Object"),
        "header_lines_to_skip": Param(
            1, type="integer", title="Header Lines to Skip", min=0
        ),
        "footer_lines_to_skip": Param(
            1, type="integer", title="Footer Lines to Skip", min=0
        ),
    },
)
def gcs_file_processor():
    """
    ### GCS File Processor DAG

    This DAG demonstrates how to use the `KubernetesPodOperator` to download a file
    from Google Cloud Storage, strip a specified number of header and footer lines,
    and upload the result back to GCS.

    It assumes the GKE cluster has Workload Identity enabled, allowing pods to
    authenticate with GCP services.

    **To run this DAG:**
    1.  Update the placeholder values for `GCS_BUCKET`, `INPUT_OBJECT`, and `OUTPUT_OBJECT`.
    2.  Create a sample file and upload it to `gs://<your-gcs-bucket-name>/<path/to/your/input_file.txt>`.
    3.  Trigger the DAG, optionally overriding the default parameters.
    """

    # The bash script to be executed in the pod.
    # It uses Jinja templating to access the DAG's parameters.
    bash_script = """
    set -euo pipefail
    INPUT_GCS_PATH="gs://{{ params.gcs_bucket }}/{{ params.input_object }}"
    OUTPUT_GCS_PATH="gs://{{ params.gcs_bucket }}/{{ params.output_object }}"
    HEADER_LINES={{ params.header_lines_to_skip }}
    FOOTER_LINES={{ params.footer_lines_to_skip }}

    echo "Streaming from ${INPUT_GCS_PATH}, stripping ${HEADER_LINES} header(s) and ${FOOTER_LINES} footer(s), and uploading to ${OUTPUT_GCS_PATH}"

    # Stream the file from GCS, pipe it through tail and head to strip lines,
    # and then stream the result back to a new GCS object.
    # This avoids saving the file locally in the pod.
    # `tail -n +N` starts from line N; `head -n -M` outputs all but the last M lines.
    gcloud storage cp "${INPUT_GCS_PATH}" - | tail -n +$((HEADER_LINES + 1)) | head -n -"${FOOTER_LINES}" | gcloud storage cp - "${OUTPUT_GCS_PATH}"

    echo "Stream processing complete. Job finished."
    """

    KubernetesPodOperator(
        task_id="process_gcs_file",
        name="gcs-file-processor-pod",
        namespace="composer-user-workloads",
        image="gcr.io/google.com/cloudsdktool/cloud-sdk:latest",
        cmds=["bash"],
        arguments=["-c", bash_script],
        config_file="/home/airflow/composer_kube_config",
        kubernetes_conn_id="kubernetes_default",
        log_events_on_failure=True,
        do_xcom_push=False,
    )


# Instantiate the DAG
gcs_file_processor()