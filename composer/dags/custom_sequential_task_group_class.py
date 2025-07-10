from time import sleep

from airflow import models
from airflow.decorators import task, task_group
from airflow.exceptions import AirflowFailException
from airflow.utils.task_group import TaskGroup


class CustomSequentialTaskGroup(TaskGroup):
    def __init__(self, group_id, files=["file1"], **kwargs):
        super().__init__(group_id=group_id, **kwargs)

        @task_group(parent_group=self)
        def parallel_task_group(file):
            @task
            def task_1(file):
                print(f"file: {file}")
                return file

            return task_1(file)

        @task(task_group=self)
        def combine_files_before_sequential_processing(files):
            print(f"files: {files}")
            return files

        @task_group(parent_group=self)
        def sequential_task_group(file):
            @task(max_active_tis_per_dag=1)
            def task_1(file, ti):
                if ti.map_index > 0:

                    def get_upstream_dependency(ti):
                        return models.TaskInstance.get_task_instance(
                            ti.dag_id,
                            ti.run_id,
                            f"my_custom_task_group.sequential_task_group.task_2",
                            ti.map_index - 1,
                        )

                    dependency_ti = get_upstream_dependency(ti)
                    while (
                        dependency_ti.state is None
                        or dependency_ti.state
                        in [
                            "scheduled",  # The scheduler has determined the Task’s dependencies are met and it should run
                            "queued",  # The task has been assigned to an Executor and is awaiting a worker
                            "running",  # The task is running on a worker (or on a local/synchronous executor)
                            # "success", # The task finished running without errors
                            "restarting",  # The task was externally requested to restart when it was running
                            # "failed", # The task had an error during execution and failed to run
                            # "skipped", # The task was skipped due to branching, LatestOnly, or similar.
                            # "upstream_failed", # An upstream task failed and the Trigger Rule says we needed it
                            "up_for_retry",  # The task failed, but has retry attempts left and will be rescheduled.
                            "up_for_reschedule",  # The task is a Sensor that is in reschedule mode
                            "deferred",  # The task has been deferred to a trigger
                            # "removed", # The task has vanished from the DAG since the run started
                        ]
                    ):
                        sleep(60)  # Poll every minute
                        dependency_ti = get_upstream_dependency(ti)
                    if dependency_ti in ["failed", "upstream_failed"]:
                        raise AirflowFailException(
                            "Upstream task failed in sequential dynamic task run."
                        )

                print(f"task_1: {file=}")
                return file

            @task(max_active_tis_per_dag=1)
            def task_2(file):
                print(f"task_2: {file=}")

            task_2(task_1(file))

        task_group_1_files = parallel_task_group.expand(file=files)
        reduced_files = combine_files_before_sequential_processing(task_group_1_files)
        sequential_task_group.expand(file=reduced_files)
