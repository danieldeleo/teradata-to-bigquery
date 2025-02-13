from airflow.decorators import dag
import sys
print(sys.path)
import custom_task_group_class


@dag(schedule=None, catchup=False)
def custom_tg():
    ctg = custom_task_group_class.CustomTaskGroup(
        group_id="my_custom_task_group", files=["file1", "file2", "file3", "file4"]
    )


custom_tg()
