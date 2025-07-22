from airflow import models
from airflow.decorators import task
from airflow.utils.task_group import TaskGroup


class CustomSleepyTaskGroup(TaskGroup):
    def __init__(self, group_id, seconds=0, **kwargs):
        super().__init__(group_id=group_id, add_suffix_on_collision=True, **kwargs)

        @task(task_group=self)
        def sleep_for(seconds):
            from time import sleep
            sleep(seconds)
            return seconds
        
        @task(task_group=self)
        def more_sleep_for(seconds):
            from time import sleep
            sleep(seconds)
            return seconds
        
        @task(task_group=self)
        def even_more_sleep_for(seconds):
            from time import sleep
            sleep(seconds)
            return seconds
        
        even_more_sleep_for(more_sleep_for(sleep_for(seconds)))

        
