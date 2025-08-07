from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Callable, Iterable, Sequence

import httpx
from airflow.configuration import conf
from airflow.exceptions import AirflowException, AirflowSkipException
from airflow.providers.google.cloud.hooks.cloud_composer import (
    CloudComposerAsyncHook,
    CloudComposerHook,
)
from airflow.sensors.base import BaseSensorOperator
from airflow.triggers.base import BaseTrigger, TriggerEvent
from airflow.utils.state import DagRunState, TaskInstanceState
from google.auth.transport.requests import Request
from google.oauth2 import id_token

if TYPE_CHECKING:
    from airflow.utils.context import Context
    from pendulum import DateTime


class CloudComposerExternalTaskSensor(BaseSensorOperator):
    """
    Waits for a task to complete in a different Cloud Composer environment.

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
        Checks the status of the external task.

        Returns a tuple of (status, message).
        Status can be 'success', 'failed', 'skipped', 'running', 'pending'.
        """
        try:
            environment = hook.get_environment(
                project_id=self.project_id,
                region=self.region,
                environment_id=self.environment_id,
            )
            airflow_uri = environment.config.airflow_uri

            # Get client_id, supporting both Composer 2 and 3.
            # Path for Composer 3.
            client_id = getattr(environment.config.web_server_config, "client_id", None)
            # Path for Composer 2.
            if not client_id:
                try:
                    client_id = environment.config.web_server_network_access_control.iap_config.oauth2_client_id
                except AttributeError:
                    pass  # If this also fails, we'll raise an error below.

            if not client_id:
                raise AirflowException(
                    "Could not find IAP client_id for the Composer environment. "
                    "This might be because IAP is not enabled or due to a permissions issue."
                )

            creds = hook._get_credentials()
            if not creds.valid:
                creds.refresh(Request())
            id_token_str = id_token.fetch_id_token(Request(), client_id)

            headers = {"Authorization": f"Bearer {id_token_str}"}

            # 1. Find DAG run
            dag_run_url = f"{airflow_uri}/api/v1/dags/{self.external_dag_id}/dagRuns"
            params = {
                "execution_date_gte": execution_date.isoformat(),
                "execution_date_lte": execution_date.isoformat(),
            }

            response = httpx.get(
                dag_run_url, params=params, headers=headers, timeout=self.poke_interval
            )
            response.raise_for_status()
            dag_runs = response.json()["dag_runs"]

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

            # 2. Get Task Instance status
            task_instance_url = f"{airflow_uri}/api/v1/dags/{self.external_dag_id}/dagRuns/{dag_run_id}/taskInstances/{self.external_task_id}"

            response = httpx.get(
                task_instance_url, headers=headers, timeout=self.poke_interval
            )

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

        except httpx.HTTPStatusError as e:
            self.log.error("HTTP error while checking task status: %s", e)
            return "pending", f"HTTP error: {e}"
        except Exception as e:
            self.log.error("Error checking task status: %s", e, exc_info=True)
            raise AirflowException(f"Error checking task status: {e}") from e

    def execute(self, context: Context) -> Any:
        if not self.deferrable:
            super().execute(context)
        else:
            execution_date = self._get_target_execution_date(context)
            self.defer(
                trigger=CloudComposerExternalTaskTrigger(
                    project_id=self.project_id,
                    region=self.region,
                    environment_id=self.environment_id,
                    external_dag_id=self.external_dag_id,
                    external_task_id=self.external_task_id,
                    allowed_states=self.allowed_states,
                    failed_states=self.failed_states,
                    execution_date_iso=execution_date.isoformat(),
                    gcp_conn_id=self.gcp_conn_id,
                    impersonation_chain=self.impersonation_chain,
                    poll_interval=self.poke_interval,
                ),
                method_name="execute_complete",
            )

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


class CloudComposerExternalTaskTrigger(BaseTrigger):
    """A trigger that polls for the status of a task in another Cloud Composer environment."""

    def __init__(
        self,
        project_id: str,
        region: str,
        environment_id: str,
        external_dag_id: str,
        external_task_id: str,
        allowed_states: list[str],
        failed_states: list[str],
        execution_date_iso: str,
        gcp_conn_id: str,
        impersonation_chain: str | Sequence[str] | None,
        poll_interval: int,
    ):
        super().__init__()
        self.project_id = project_id
        self.region = region
        self.environment_id = environment_id
        self.external_dag_id = external_dag_id
        self.external_task_id = external_task_id
        self.allowed_states = allowed_states
        self.failed_states = failed_states
        self.execution_date_iso = execution_date_iso
        self.gcp_conn_id = gcp_conn_id
        self.impersonation_chain = impersonation_chain
        self.poll_interval = poll_interval

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return (
            "custom_composer_external_task_sensor.CloudComposerExternalTaskTrigger",
            {
                "project_id": self.project_id,
                "region": self.region,
                "environment_id": self.environment_id,
                "external_dag_id": self.external_dag_id,
                "external_task_id": self.external_task_id,
                "allowed_states": self.allowed_states,
                "failed_states": self.failed_states,
                "execution_date_iso": self.execution_date_iso,
                "gcp_conn_id": self.gcp_conn_id,
                "impersonation_chain": self.impersonation_chain,
                "poll_interval": self.poll_interval,
            },
        )

    @staticmethod
    def _get_identity_token(hook: CloudComposerHook, audience: str) -> str:
        """Helper sync function to be run in a thread."""
        creds = hook._get_credentials()
        if not creds.valid:
            creds.refresh(Request())
        return id_token.fetch_id_token(Request(), audience)

    async def run(self):
        hook = CloudComposerAsyncHook(
            gcp_conn_id=self.gcp_conn_id,
            impersonation_chain=self.impersonation_chain,
        )
        sync_hook = CloudComposerHook(
            gcp_conn_id=self.gcp_conn_id,
            impersonation_chain=self.impersonation_chain,
        )
        try:
            environment = await hook.get_environment(
                project_id=self.project_id,
                region=self.region,
                environment_id=self.environment_id,
            )
            airflow_uri = environment.config.airflow_uri
            # Get client_id, supporting both Composer 2 and 3.
            # Path for Composer 3.
            client_id = getattr(environment.config.web_server_config, "client_id", None)
            # Path for Composer 2.
            if not client_id:
                try:
                    client_id = environment.config.web_server_network_access_control.iap_config.oauth2_client_id
                except AttributeError:
                    pass  # If this also fails, we'll raise an error below.

            if not client_id:
                raise AirflowException(
                    "Could not find IAP client_id for the Composer environment. "
                    "This might be because IAP is not enabled or due to a permissions issue."
                )

            async with httpx.AsyncClient() as client:
                while True:
                    try:
                        id_token_str = await asyncio.to_thread(
                            self._get_identity_token, sync_hook, client_id
                        )
                        headers = {"Authorization": f"Bearer {id_token_str}"}

                        # 1. Find DAG run
                        dag_run_url = (
                            f"{airflow_uri}/api/v1/dags/{self.external_dag_id}/dagRuns"
                        )
                        params = {
                            "execution_date_gte": self.execution_date_iso,
                            "execution_date_lte": self.execution_date_iso,
                        }

                        response = await client.get(
                            dag_run_url,
                            params=params,
                            headers=headers,
                            timeout=self.poll_interval,
                        )

                        if response.status_code == 200:
                            dag_runs = response.json()["dag_runs"]
                            if dag_runs:
                                dag_run = dag_runs[-1]
                                dag_run_id = dag_run["dag_run_id"]
                                dag_run_state = dag_run["state"]

                                if dag_run_state == DagRunState.FAILED:
                                    yield TriggerEvent(
                                        {
                                            "status": "failed",
                                            "message": f"External DAG run for {self.external_dag_id} failed.",
                                        }
                                    )
                                    return

                                # 2. Get Task Instance status
                                task_instance_url = f"{airflow_uri}/api/v1/dags/{self.external_dag_id}/dagRuns/{dag_run_id}/taskInstances/{self.external_task_id}"

                                response = await client.get(
                                    task_instance_url,
                                    headers=headers,
                                    timeout=self.poll_interval,
                                )

                                if response.status_code == 200:
                                    task_instance = response.json()
                                    task_state = task_instance.get("state")

                                    self.log.info(
                                        "Task '%s' in DAG '%s' is in state: %s",
                                        self.external_task_id,
                                        self.external_dag_id,
                                        task_state,
                                    )

                                    if task_state in self.failed_states:
                                        yield TriggerEvent(
                                            {
                                                "status": "failed",
                                                "message": f"External task {self.external_task_id} failed with state: {task_state}",
                                            }
                                        )
                                        return

                                    if task_state in self.allowed_states:
                                        yield TriggerEvent(
                                            {
                                                "status": "success",
                                                "message": f"External task {self.external_task_id} is in state: {task_state}",
                                            }
                                        )
                                        return
                                elif response.status_code != 404:
                                    response.raise_for_status()
                    except Exception as e:
                        self.log.warning(
                            "Error while polling for task status: %s. Retrying...",
                            e,
                            exc_info=True,
                        )

                    await asyncio.sleep(self.poll_interval)
        except Exception as e:
            yield TriggerEvent({"status": "error", "message": str(e)})
