from airflow.decorators import dag
from custom_parallel_task_group_class import CustomParallelTaskGroup


@dag(schedule=None, catchup=False)
def custom_parallel_task_group_example():
    ctg = CustomParallelTaskGroup(
        group_id="my_custom_task_group", files=["file1", "file2", "file3", "file4", "file5"]
    )


custom_parallel_task_group_example()
