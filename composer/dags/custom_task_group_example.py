from airflow.decorators import dag, task

from custom_task_group_class import CustomTaskGroup


@dag(schedule=None, catchup=False)
def custom_tg():
    ctg = CustomTaskGroup(
        group_id="my_custom_task_group", files=["file1", "file2", "file3", "file4"]
    )


custom_tg()
