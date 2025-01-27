import pytest
import pathlib

from airflow.models import DagBag


@pytest.fixture()
def dagbag():
    return DagBag("../dags", include_examples=False)


def test_dag_import_errors(dagbag):
    assert dagbag.import_errors == {}, "No import errors should be found"


def test_dag_import_warnings(dagbag):
    assert dagbag.captured_warnings == {}, "No warnings should be captured"