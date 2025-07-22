from airflow.decorators import dag, task
from custom_sleepy_task_group_class import CustomSleepyTaskGroup

files = ["file1", "file2", "file3", "file4", "file5"]

@dag(schedule=None, catchup=False)
def custom_sleepy_task_group_example():
    @task
    def get_sleepy_seconds():
        return [5,5,5,5,5]
    
    @task_group
    def sleepy_task_group(seconds):
        CustomSleepyTaskGroup(group_id="my_custom_sleepy_task_group", seconds=seconds)
    
    sleepy_task_group.expand(seconds=get_sleepy_seconds())


custom_sleepy_task_group_example()
