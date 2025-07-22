from airflow.decorators import dag

from custom_sequential_task_group_class import CustomSequentialTaskGroup


@dag(schedule=None, catchup=False)
def custom_sequential_task_group_example():
    ctg = CustomSequentialTaskGroup(
        group_id="my_custom_task_group",
        files=["file1", "file2", "file3", "file4", "file5"],
    )


custom_sequential_task_group_example()
