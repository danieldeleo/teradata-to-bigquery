import sys
from pathlib import Path

import pytest
from airflow.models import DagBag
from pendulum.tz.timezone import Timezone


@pytest.fixture(scope="session")
def dagbag():
    dags_path = str((Path(__file__).parent.parent / "dags").resolve())
    sys.path.insert(0, dags_path)
    yield DagBag(dag_folder=dags_path, include_examples=False)

def test_dagbag_not_empty(dagbag):
    assert dagbag.size() > 0, "Dagbag should not be empty."

def test_dagbag_no_import_errors(dagbag):
    assert dagbag.import_errors == {}, "No import errors should be found."

''' Uncomment below if you want to fail on warnings
def test_dagbag_no_import_warnings(dagbag):
    assert len(dagbag.captured_warnings) == 0, "No warnings should be found."
'''

def test_filename_matches_dag_id(dagbag):
    """Tests that filename matches dag_id"""
    for dag in dagbag.dags.values():
        assert dag.dag_id == Path(dag.relative_fileloc).stem, (
            "Filename does not match DAG ID."
        )

def test_sleepy_dag(dagbag):
    dag = dagbag.get_dag("sleepy")
    assert dag is not None, "DAG sleepy not found."
    assert len(dag.tasks) == 3, "DAG sleepy should contain 3 tasks."


# def test_custom_task_group_example(dagbag):
#     dag = dagbag.get_dag("custom_task_group_example")
#     assert dag is not None, "DAG custom_task_group_example not found."
#     assert len(dag.tasks) == 4, "DAG custom_task_group_example should contain 4 tasks."

def test_timezone_aware_dag(dagbag):
    dag = dagbag.get_dag("gcs_object_existence_sensor_test")
    assert dag.timezone == Timezone("America/New_York"), "DAG timezone should be America/New_York."