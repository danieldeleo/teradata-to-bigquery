from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from airflow.exceptions import AirflowException
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.session import provide_session

if TYPE_CHECKING:
    from airflow.utils.context import Context
    from sqlalchemy.orm.session import Session


class CustomExternalTaskSensor(ExternalTaskSensor):
    """
    Waits for a task or DAG to complete in a different DAG.

    This sensor is a subclass of `ExternalTaskSensor` and adds the ability to
    wait for a specific DAG run by providing an `external_dag_run_id`.

    If `external_dag_run_id` is provided, the sensor will look for that
    specific `run_id`. Otherwise, it will fall back to the behavior of the
    `ExternalTaskSensor` which uses execution dates to find the target DAG run.

    :param external_dag_run_id: The `run_id` of the DAG run to wait for.
        If provided, `execution_date_fn` and `execution_delta` are ignored.
    :param external_task_map_index: The `map_index` of the mapped task to wait for.
        Only works when `external_dag_run_id` is provided and `external_task_id` is used.
    """

    template_fields: Sequence[str] = (
        *ExternalTaskSensor.template_fields,
        "external_dag_run_id",
        "external_task_map_index",
    )

    def __init__(
        self,
        *,
        external_dag_run_id: str | None = None,
        external_task_map_index: int | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.external_dag_run_id = external_dag_run_id
        self.external_task_map_index = external_task_map_index

        if self.external_dag_run_id and (
            self.execution_date_fn or self.execution_delta
        ):
            self.log.warning(
                "`external_dag_run_id` is provided, so `execution_date_fn` and `execution_delta` will be ignored."
            )
        if self.external_task_map_index is not None:
            if not self.external_dag_run_id:
                raise AirflowException(
                    "`external_task_map_index` is only supported when `external_dag_run_id` is provided."
                )
            if self.external_task_ids:
                raise AirflowException(
                    "`external_task_map_index` is not supported with `external_task_ids`."
                )

    @provide_session
    def poke(self, context: Context, session: Session) -> bool:
        if self.external_dag_run_id:
            return self._poke_for_dag_run(session)
        return super().poke(context, session=session)

    def _poke_for_dag_run(self, session: Session) -> bool:
        from airflow.models.dagrun import DagRun
        from airflow.models.taskinstance import TaskInstance

        log_message = f"Poking for external DAG '{self.external_dag_id}' with run_id '{self.external_dag_run_id}'"
        if self.external_task_id or self.external_task_ids:
            tasks = self.external_task_id or self.external_task_ids
            log_message += f", task(s) '{tasks}'"
            if self.external_task_map_index is not None:
                log_message += f", map_index {self.external_task_map_index}"
        self.log.info(log_message)

        dag_run = (
            session.query(DagRun)
            .filter(
                DagRun.dag_id == self.external_dag_id,
                DagRun.run_id == self.external_dag_run_id,
            )
            .one_or_none()
        )

        if not dag_run:
            self.log.info(
                "DAG run '%s' not found for DAG '%s'. Poking again.",
                self.external_dag_run_id,
                self.external_dag_id,
            )
            return False

        if dag_run.state in self.failed_states:
            raise AirflowException(
                f"External DAG run '{self.external_dag_run_id}' failed with state: {dag_run.state}"
            )

        if not self.external_task_id and not self.external_task_ids:
            if dag_run.state in self.allowed_states:
                self.log.info(
                    "External DAG run '%s' is in allowed state: %s",
                    self.external_dag_run_id,
                    dag_run.state,
                )
                return True
            self.log.info(
                "DAG run '%s' is in state '%s'. Poking again.",
                self.external_dag_run_id,
                dag_run.state,
            )
            return False

        task_ids_to_check = (
            {self.external_task_id}
            if self.external_task_id
            else set(self.external_task_ids or [])
        )

        query = session.query(TaskInstance).filter(
            TaskInstance.dag_id == self.external_dag_id,
            TaskInstance.run_id == self.external_dag_run_id,
            TaskInstance.task_id.in_(task_ids_to_check),
        )

        if self.external_task_map_index is not None:
            query = query.filter(TaskInstance.map_index == self.external_task_map_index)

        failed_tis = query.filter(TaskInstance.state.in_(self.failed_states)).all()
        if failed_tis:
            failed_tasks_str = ", ".join(
                f"'{ti.task_id}' (map_index={ti.map_index}, state={ti.state})"
                for ti in failed_tis
            )
            raise AirflowException(
                f"External task(s) {failed_tasks_str} failed in DAG run {self.external_dag_run_id}."
            )

        count_allowed = query.filter(
            TaskInstance.state.in_(self.allowed_states)
        ).count()
        total_count = query.count()
        if total_count == 0:
            self.log.info(
                "No task instances found for specified criteria. Poking again."
            )
            return False

        if count_allowed == total_count:
            self.log.info(
                "All %d external task instance(s) are in allowed states.", total_count
            )
            return True

        self.log.info(
            "Found %d task instances in allowed states. Waiting for %d. Poking again.",
            count_allowed,
            total_count,
        )
        return False
