# Import necessary libraries
from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.providers.google.cloud.operators.gcs import GCSDeleteObjectsOperator

# Define the GCS bucket and object (file) to check for
GCS_BUCKET = "dannybq"  # <--- CHANGE THIS to your bucket name
GCS_OBJECT = "airflowsensortest/trigger.txt" # <--- CHANGE THIS to the object path you expect

# Define default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retry_delay": pendulum.duration(minutes=5),
}

# Define the DAG
with DAG(
    dag_id="gcs_object_existence_sensor_test",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"), # Adjust start date as needed
    schedule=None, # Can be set to a schedule string like "@daily" or None for manual runs
    catchup=False,
    default_args=default_args,
    tags=["gcs", "sensor", "deferrable", "example"],
    description="Example DAG using GCSObjectExistenceSensor in deferrable mode.",
) as dag:
    # Task 1: Start task (optional, good practice)
    start = EmptyOperator(task_id="start")

    # Task 2: Sensor task waiting for the GCS object in deferrable mode
    wait_for_gcs_file = GCSObjectExistenceSensor(
        task_id="wait_for_gcs_file",
        bucket=GCS_BUCKET,
        object=GCS_OBJECT,
        deferrable=True,  # --- This enables deferrable mode ---
        # Optional: Define how long the sensor should wait before timing out
        # timeout=60 * 60 * 2, # Timeout after 2 hours (optional)
        # Optional: Polling interval when not deferred (less relevant in deferrable mode)
        poke_interval=1, # Check every 60 seconds (when not deferred)
        # Optional: Exponential backoff for retries if needed
        # exponential_backoff=True,
    )

    delete_trigger_file = GCSDeleteObjectsOperator(
        task_id="delete_trigger_file",
        bucket=GCS_BUCKET,
        objects=[GCS_OBJECT],
        # Optional: Set to True to delete the file even if it doesn't exist
        ignore_if_missing=True,
    )

    # Task 3: Downstream task that runs after the file is detected
    processing_complete = EmptyOperator(task_id="processing_complete")

    # Define task dependencies
    start >> wait_for_gcs_file >> delete_trigger_file >> processing_complete