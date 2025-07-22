from airflow.decorators import dag, task
from custom_parallel_task_group_class import CustomParallelTaskGroup


@dag(schedule=None, catchup=False)
def custom_parallel_task_group_example():
    @task
    def get_files():
        return ["file1", "file2", "file3", "file4", "file5"]
    ctg = CustomParallelTaskGroup(
        group_id="my_custom_task_group"
    )
    ctg.expand(files=get_files())


custom_parallel_task_group_example()
