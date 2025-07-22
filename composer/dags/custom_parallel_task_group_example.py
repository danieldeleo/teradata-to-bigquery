from airflow.decorators import dag
from custom_parallel_task_group_class import CustomParallelTaskGroup

files = ["file1", "file2", "file3", "file4", "file5"]

@dag(schedule=None, catchup=False)
def custom_parallel_task_group_example():
    ctg = CustomParallelTaskGroup(
        group_id="my_custom_task_group", files=files
    )
    ctg2 = CustomParallelTaskGroup(
        group_id="my_custom_task_group", files=files
    )
    ctg3 = CustomParallelTaskGroup(
        group_id="my_custom_task_group", files=files
    )
    ctg >> ctg2 >> ctg3


custom_parallel_task_group_example()
