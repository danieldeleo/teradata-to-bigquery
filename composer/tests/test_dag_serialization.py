from pathlib import Path
import sys
import tempfile
from shutil import copytree

import pytest
from airflow.models import DagBag

DAG_DIRS = ["dags"]


@pytest.fixture(scope="session")
def dagbag():
    """Copies contents of dags/ folders to a temporary directory"""
    temp_dir = tempfile.mkdtemp()
    for d in DAG_DIRS:
        copytree(
            Path(__file__).parent.parent / d ,
            f"{temp_dir}/",
            dirs_exist_ok=True,
        )
    sys.path.insert(0, temp_dir)
    yield DagBag(dag_folder=temp_dir, include_examples=False)

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
