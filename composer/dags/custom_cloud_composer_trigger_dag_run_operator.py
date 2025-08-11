from __future__ import annotations

import json
from typing import Any, Sequence

import pendulum
import requests
from airflow.exceptions import AirflowException
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.google.cloud.hooks.cloud_composer import CloudComposerHook
from airflow.utils.context import Context
from google.auth.transport.requests import AuthorizedSession


class CloudComposerTriggerDagRunOperator(TriggerDagRunOperator):
    """
    Triggers a DAG run in a separate Cloud Composer environment using the Airflow REST API.

    This operator extends the standard `TriggerDagRunOperator` to allow triggering
    DAGs in a different Composer environment.

    **Important Note on `wait_for_completion`:**
    The `wait_for_completion` parameter inherited from `TriggerDagRunOperator`
    is **not supported** for external Composer environments due to the inability
    to directly query the external Airflow metadata database. If `wait_for_completion`
    is set to `True`, an `AirflowException` will be raised.
    To wait for the triggered external DAG run or a specific task within it to finish,
    consider chaining this operator with a sensor like `CloudComposerExternalTaskSensor`.

    :param project_id: The GCP project ID of the external Composer environment.
    :param region: The region of the external Composer environment.
    :param environment_id: The name of the external Composer environment.
    :param trigger_dag_id: The dag_id of the DAG to trigger in the external environment.
    :param conf: Configuration dictionary to pass to the triggered DAG run.
    :param logical_date: The logical date (execution date) to assign to the
        triggered DAG run. If None, the logical date of the current DAG run
        will be used. This should be a pendulum.DateTime object or a string
        that can be parsed by pendulum.parse().
    :param gcp_conn_id: The connection ID to use when fetching connection info.
    :param impersonation_chain: Optional service account to impersonate.
    """

    # Add new template fields for Composer environment details
    template_fields: Sequence[str] = (
        *TriggerDagRunOperator.template_fields,  # Inherit existing template fields
        "project_id",
        "region",
        "environment_id",
        "impersonation_chain",
    )

    def __init__(
        self,
        *,
        project_id: str,
        region: str,
        environment_id: str,
        trigger_dag_id: str,
        conf: dict | None = None,
        logical_date: pendulum.DateTime | str | None = None,
        gcp_conn_id: str = "google_cloud_default",
        impersonation_chain: str | Sequence[str] | None = None,
        **kwargs,
    ) -> None:
        # Pass relevant arguments to the parent constructor
        super().__init__(
            trigger_dag_id=trigger_dag_id,
            conf=conf,
            logical_date=logical_date,
            **kwargs,
        )
        self.project_id = project_id
        self.region = region
        self.environment_id = environment_id
        self.gcp_conn_id = gcp_conn_id
        self.impersonation_chain = impersonation_chain

        # Enforce the limitation for wait_for_completion
        if self.wait_for_completion:
            raise AirflowException(
                "`wait_for_completion=True` is not supported for `CloudComposerTriggerDagRunOperator`. "
                "Please use `wait_for_completion=False` and chain with a `CloudComposerExternalTaskSensor` "
                "or similar sensor to wait for the external DAG run."
            )

    def _do_trigger_dagrun(self, context: Context) -> dict[str, Any]:
        """
        Overrides the parent method to trigger a DAG run in an external Composer environment.
        """
        hook = CloudComposerHook(
            gcp_conn_id=self.gcp_conn_id,
            impersonation_chain=self.impersonation_chain,
        )

        environment = hook.get_environment(
            project_id=self.project_id,
            region=self.region,
            environment_id=self.environment_id,
        )
        airflow_uri = environment.config.airflow_uri

        credentials = hook.get_credentials()
        authed_session = AuthorizedSession(credentials)

        # Generate a unique dag_run_id. Using ts_nodash from context is common.
        # The Airflow API expects a string.
        dag_run_id = f"manual__{context['ts_nodash']}"

        # Determine the logical_date for the triggered DAG run.
        # If not provided, use the logical_date of the current DAG run.
        # Ensure it's a pendulum DateTime object for isoformat().
        target_logical_date = self.logical_date
        if target_logical_date is None:
            target_logical_date = context["logical_date"]
        elif isinstance(target_logical_date, str):
            target_logical_date = pendulum.parse(target_logical_date)

        if not isinstance(target_logical_date, pendulum.DateTime):
            raise AirflowException(
                f"Invalid logical_date type: {type(target_logical_date)}. "
                "Must be pendulum.DateTime or a string parseable by pendulum."
            )

        trigger_url = f"{airflow_uri}/api/v1/dags/{self.trigger_dag_id}/dagRuns"
        headers = {"Content-Type": "application/json"}
        payload = {
            "dag_run_id": dag_run_id,
            "logical_date": target_logical_date.isoformat(),
            "conf": self.conf,
        }

        self.log.info(
            "Attempting to trigger DAG '%s' in Composer environment '%s' (project: %s, region: %s) "
            "with run_id '%s' and logical_date '%s'.",
            self.trigger_dag_id,
            self.environment_id,
            self.project_id,
            self.region,
            dag_run_id,
            target_logical_date.isoformat(),
        )

        try:
            response = authed_session.post(
                trigger_url, headers=headers, data=json.dumps(payload), timeout=60
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            triggered_dag_run = response.json()
            self.log.info(
                "Successfully triggered DAG '%s'. Triggered DAG Run ID: %s, State: %s",
                self.trigger_dag_id,
                triggered_dag_run.get("dag_run_id"),
                triggered_dag_run.get("state"),
            )
            # Return information about the triggered DAG run for XComs
            return {
                "dag_run_id": triggered_dag_run.get("dag_run_id"),
                "logical_date": triggered_dag_run.get("logical_date"),
                "state": triggered_dag_run.get("state"),
            }
        except requests.exceptions.HTTPError as e:
            self.log.error(
                "HTTP error triggering DAG '%s': Status %s - Response: %s",
                self.trigger_dag_id,
                e.response.status_code,
                e.response.text,
            )
            raise AirflowException(f"Failed to trigger DAG: {e}") from e
        except requests.exceptions.RequestException as e:
            self.log.error(
                "Network or API error while triggering DAG '%s': %s",
                self.trigger_dag_id,
                e,
            )
            raise AirflowException(f"Failed to trigger DAG: {e}") from e
