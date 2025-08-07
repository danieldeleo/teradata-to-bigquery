from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, Sequence

import requests
from airflow.configuration import conf
from airflow.exceptions import AirflowException, AirflowSkipException
from airflow.providers.google.cloud.hooks.cloud_composer import (
    CloudComposerHook,
)
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.state import DagRunState, TaskInstanceState
from google.auth.transport.requests import AuthorizedSession

if TYPE_CHECKING:
    from airflow.utils.context import Context
    from pendulum import DateTime


class CloudComposerExternalTaskSensor(BaseSensorOperator):
    """
    Waits for a task to complete in a different Cloud Composer environment.

    .. note::
        This sensor authenticates using a GCP **access token** via ``AuthorizedSession``.
        Standard IAP-protected Composer environments require an **ID token**.
        If your environment uses IAP, this authentication method may not work.
    It uses the Airflow REST API of the external environment.

    :param project_id: The GCP project ID of the external Composer environment.
    :param region: The region of the external Composer environment.
    :param environment_id: The name of the external Composer environment.
    :param external_dag_id: The dag_id that contains the task.
    :param external_task_id: The task_id to wait for.
    :param allowed_states: Iterable of allowed states, default is ``['success']``.
    :param failed_states: Iterable of failed or dis-allowed states, default is
        ``['failed', 'skipped']``.
    :param execution_date_fn: A function that receives the execution date of the
        current task and returns the execution date of the DAG to wait for. If not
        provided, the logical date of the current DAG is used.
    :param gcp_conn_id: The connection ID to use when fetching connection info.
    :param impersonation_chain: Optional service account to impersonate.
    :param deferrable: Run sensor in deferrable mode.
    """

    template_fields: Sequence[str] = (
        "project_id",
        "region",
        "environment_id",
        "external_dag_id",
        "external_task_id",
        "impersonation_chain",
    )

    def __init__(
        self,
        *,
        project_id: str,
        region: str,
        environment_id: str,
        external_dag_id: str,
        external_task_id: str,
        allowed_states: Iterable[str] | None = None,
        failed_states: Iterable[str] | None = None,
        execution_date_fn: Callable[[DateTime], DateTime] | None = None,
        gcp_conn_id: str = "google_cloud_default",
        impersonation_chain: str | Sequence[str] | None = None,
        deferrable: bool = conf.getboolean(
            "operators", "default_deferrable", fallback=False
        ),
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.project_id = project_id
        self.region = region
        self.environment_id = environment_id
        self.external_dag_id = external_dag_id
        self.external_task_id = external_task_id
        self.allowed_states = (
            list(allowed_states) if allowed_states else [TaskInstanceState.SUCCESS]
        )
        self.failed_states = (
            list(failed_states)
            if failed_states
            else [
                TaskInstanceState.FAILED,
                TaskInstanceState.SKIPPED,
            ]
        )
        self.execution_date_fn = execution_date_fn
        self.gcp_conn_id = gcp_conn_id
        self.impersonation_chain = impersonation_chain
        self.deferrable = deferrable

    def _get_target_execution_date(self, context: Context) -> DateTime:
        if self.execution_date_fn:
            return self.execution_date_fn(context["logical_date"])
        return context["logical_date"]

    def poke(self, context: Context) -> bool:
        execution_date = self._get_target_execution_date(context)
        self.log.info(
            "Poking for task '%s' in DAG '%s' in project '%s' at execution date %s ...",
            self.external_task_id,
            self.external_dag_id,
            self.project_id,
            execution_date,
        )

        hook = CloudComposerHook(
            gcp_conn_id=self.gcp_conn_id,
            impersonation_chain=self.impersonation_chain,
        )

        status, message = self._check_task_status(hook, execution_date)

        if status == "success":
            return True
        if status == "failed":
            raise AirflowException(message)
        if status == "skipped":
            raise AirflowSkipException(message)

        return False

    def _check_task_status(
        self, hook: CloudComposerHook, execution_date: DateTime
    ) -> tuple[str, str]:
        """
        Checks the status of the external task using an access token.

        Returns a tuple of (status, message).
        Status can be 'success', 'failed', 'skipped', 'running', 'pending'.
        """
        try:
            # 1. Get environment details from the hook
            environment = hook.get_environment(
                project_id=self.project_id,
                region=self.region,
                environment_id=self.environment_id,
            )
            airflow_uri = environment.config.airflow_uri

            # 2. Create an authorized session using credentials from the hook
            credentials = hook.get_credentials()
            authed_session = AuthorizedSession(credentials)

            # 3. Find DAG run
            dag_run_url = f"{airflow_uri}/api/v1/dags/{self.external_dag_id}/dagRuns"
            params = {
                "execution_date_gte": execution_date.isoformat(),
                "execution_date_lte": execution_date.isoformat(),
            }

            response = authed_session.get(
                dag_run_url, params=params, timeout=self.poke_interval
            )
            response.raise_for_status()
            dag_runs = response.json()["dag_runs"]
            print(f"{dag_runs=}")
            if not dag_runs:
                self.log.info(
                    "No DAG run found for execution date %s. Poking again.",
                    execution_date,
                )
                return "pending", "No DAG run found yet."

            dag_run = dag_runs[-1]  # Get the latest one
            dag_run_id = dag_run["dag_run_id"]
            dag_run_state = dag_run["state"]

            if dag_run_state == DagRunState.FAILED:
                return "failed", f"External DAG run for {self.external_dag_id} failed."

            # 4. Get Task Instance status
            task_instance_url = f"{airflow_uri}/api/v1/dags/{self.external_dag_id}/dagRuns/{dag_run_id}/taskInstances/{self.external_task_id}"

            response = authed_session.get(task_instance_url, timeout=self.poke_interval)

            if response.status_code == 404:
                self.log.info(
                    "Task instance '%s' not found yet for DAG run '%s'. Poking again.",
                    self.external_task_id,
                    dag_run_id,
                )
                return "pending", "Task instance not found yet."

            response.raise_for_status()
            task_instance = response.json()
            task_state = task_instance.get("state")

            self.log.info(
                "Found task '%s' with state '%s'", self.external_task_id, task_state
            )

            if task_state in self.failed_states:
                return (
                    "failed",
                    f"External task {self.external_task_id} in DAG {self.external_dag_id} failed with state: {task_state}",
                )

            if task_state in self.allowed_states:
                return (
                    "success",
                    f"External task {self.external_task_id} in DAG {self.external_dag_id} is in state: {task_state}",
                )

            return "running", f"Task is in state {task_state}."

        except requests.exceptions.HTTPError as e:
            # Treat 404 not as an error but as a pending state.
            if e.response is not None and e.response.status_code == 404:
                return "pending", "Upstream DAG/task not found yet."
            raise AirflowException(f"HTTP error while checking task status: {e}") from e
        except Exception as e:
            self.log.error("Error checking task status: %s", e, exc_info=True)
            raise AirflowException(f"Error checking task status: {e}") from e

    def execute(self, context: Context) -> Any:
        if not self.deferrable:
            super().execute(context)

    def execute_complete(
        self, context: Context, event: dict[str, Any] | None = None
    ) -> None:
        if event is None:
            raise AirflowException("Did not receive an event from the triggerer")

        status = event.get("status")
        message = event.get("message")

        if status == "success":
            self.log.info(message)
            return
        if status == "skipped":
            raise AirflowSkipException(message)

        raise AirflowException(message)
