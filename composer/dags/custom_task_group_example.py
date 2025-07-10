from airflow.decorators import dag
from composer.dags.custom_sequential_task_group_class import CustomTaskGroup


@dag(schedule=None, catchup=False)
def custom_sequential_task_group_example():
    ctg = CustomTaskGroup(
        group_id="my_custom_task_group", files=["file1", "file2", "file3", "file4", "file5"]
    )


custom_sequential_task_group_example()
