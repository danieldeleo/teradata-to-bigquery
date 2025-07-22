from airflow.decorators import dag, task, task_group

from custom_sleepy_task_group_class import CustomSleepyTaskGroup


@dag(schedule=None, catchup=False)
def custom_sleepy_task_group_example():
    @task
    def get_sleepy_seconds():
        return [5, 4, 3, 2, 1]

    @task_group
    def sleepy_task_group(seconds):
        sleep1 = CustomSleepyTaskGroup(
            group_id="my_custom_sleepy_task_group_1",
            seconds=seconds
        )
        sleep2 = CustomSleepyTaskGroup(
            group_id="my_custom_sleepy_task_group_2",
            seconds=sleep1
        )
        sleep3 = CustomSleepyTaskGroup(
            group_id="my_custom_sleepy_task_group_3",
            seconds=sleep2
        )
        return sleep3.output

    @task
    def done_sleeping(seconds):
        print(f"Done sleeping for {seconds=}")

    out = sleepy_task_group.expand(seconds=get_sleepy_seconds())
    done_sleeping(out)


custom_sleepy_task_group_example()
