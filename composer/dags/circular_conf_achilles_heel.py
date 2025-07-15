# Import necessary libraries
from __future__ import annotations

from airflow.models.dag import DAG
from airflow.utils.dates import days_ago
from airflow.operators.empty import EmptyOperator
from airflow.operators.python_operator import PythonOperator # type: ignore
import json
from copy import deepcopy


# Trigger this DAG with the following dynamic config:
# {"steps":[{"name":"middle", "type":"middle", "params":{"steps":{}}}]}
with DAG(
        dag_id="circular_conf_achilles_heel",
        start_date=days_ago(1),
        schedule=None,
        catchup=False,
        max_active_runs=1,
        default_args={
            "retries": 0
        },
        description="Example of a DAG which can cause Airflow Scheduler to endlessly restart itself, rendering Composer inoperable.",
    ) as dag:

    # Start task (optional, good practice)
    start = EmptyOperator(task_id="start", dag=dag)
    
    def checkDynamicParams(context, params, taskType):
        dynamic_config = context['dag_run'].conf
        if dynamic_config != {}:
            dynamic_config = {k.lower(): v for k, v in dynamic_config.items()}
            for task in dynamic_config['steps']:
                task = {k.lower(): v for k, v in task.items()}
                if task['name'].lower() != 'start' and task['name'].lower() != 'end':
                    if task['type'].lower() == taskType :
                        params = task['params']
                        print("updated params:", params)
                        break          
                else:
                    print("no dynamic config passed for this task while triggering, proceeding with user metadata..")

        else:
            print("no dynamic config passed while triggering, proceeding with user metadata..")

        return params
    
    def _create_circular_conf(**context):
        params=None
        params = checkDynamicParams(context, params, "middle")
        print(f"params is context?: {params is context['dag_run'].conf['steps'][0]['params']}")
        # params['steps']['another_key'] = params['steps']

    def _downstream_task(**context):
        print('hello')

    create_circular_conf = PythonOperator(task_id="create_circular_conf", python_callable=_create_circular_conf)

    downstream_task = PythonOperator(task_id="downstream_task", python_callable=_downstream_task)

    # End task (optional, good practice)
    end = EmptyOperator(task_id="end", dag=dag)

    # Define task dependencies
    start >> create_circular_conf >> downstream_task >> end