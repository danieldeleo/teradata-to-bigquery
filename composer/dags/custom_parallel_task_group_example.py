from airflow.decorators import dag

from custom_parallel_task_group_class import CustomParallelTaskGroup

files = [
    {"file_name": "file1"},
    {"file_name": "file2"},
    {"file_name": "file3"},
    {"file_name": "file4"},
    {"file_name": "file5"},
]


@dag(schedule=None, catchup=False)
def custom_parallel_task_group_example():
    ctg1 = CustomParallelTaskGroup(group_id="my_custom_task_group_1", files=files)
    ctg2 = CustomParallelTaskGroup(group_id="my_custom_task_group_2", files=files)
    ctg3 = CustomParallelTaskGroup(group_id="my_custom_task_group_3", files=files)
    ctg1 >> ctg2 >> ctg3


custom_parallel_task_group_example()
