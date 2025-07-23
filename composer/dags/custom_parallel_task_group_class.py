from airflow import models
from airflow.decorators import task, task_group
from airflow.utils.task_group import TaskGroup


class CustomParallelTaskGroup(TaskGroup):
    def __init__(self, group_id, files=[], **kwargs):
        super().__init__(group_id=group_id, **kwargs)

        @task_group(parent_group=self)
        def parallel_task_group(file):
            @task(map_index_template="task1_{{file}}")
            def task_1(file):
                print(f"{file=}")
                return file

            return task_1(file)

        @task(task_group=self)
        def combine_files_before_sequential_processing(files):
            files = list(files)
            print(f"{files=}")
            return files

        @task_group(parent_group=self)
        def another_parallel_task_group(file):
            @task(map_index_template="another_task1_{{file}}")
            def task_1(file, ti):
                print(f"{file=}")
                return file

            @task(map_index_template="another_task2_{{file}}")
            def task_2(file):
                print(f"{file=}")
                return file

            return task_2(task_1(file))

        task_group_1_files = parallel_task_group.expand(file=files)
        reduced_files = combine_files_before_sequential_processing(task_group_1_files)
        another_parallel_task_group.expand(file=reduced_files)
