from airflow.decorators import dag
import sys
print(sys.path)
from custom_task_group_class import CustomTaskGroup


@dag(schedule=None, catchup=False)
def custom_task_group_example():
    ctg = CustomTaskGroup(
        group_id="my_custom_task_group", files=["file1", "file2", "file3", "file4"]
    )


custom_task_group_example()
