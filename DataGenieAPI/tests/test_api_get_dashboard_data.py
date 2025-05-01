import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Fix Python path to import main app and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app

client = TestClient(app)

@pytest.fixture
def mock_db_connection(mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mocker.patch("main.get_db_connection", return_value=mock_conn)
    return mock_conn, mock_cursor


def test_get_data_genie_metrics_success(mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection

    # Mock data for two result sets
    first_result_set_description = [("Column1",), ("Column2",)]
    first_result_set_rows = [("Value1", "Value2"), ("Value3", "Value4")]

    second_result_set_description = [("ColumnA",), ("ColumnB",)]
    second_result_set_rows = [("Value5", "Value6")]

    result_sets = [
        (first_result_set_description, first_result_set_rows),
        (second_result_set_description, second_result_set_rows)
    ]

    result_set_index = 0

    # Provide correct description dynamically based on the result set index
    type(mock_cursor).description = property(lambda self: result_sets[result_set_index][0])

    def mock_nextset():
        nonlocal result_set_index
        if result_set_index < len(result_sets) - 1:
            result_set_index += 1
            return True
        return False

    def mock_fetchall():
        return result_sets[result_set_index][1]

    mock_cursor.fetchall.side_effect = mock_fetchall
    mock_cursor.nextset.side_effect = mock_nextset

    response = client.get("/getdashboarddata")

    expected_response = {
        "status": "success",
        "result_sets": [
            {
                "columns": ["Column1", "Column2"],
                "rows": [
                    {"Column1": "Value1", "Column2": "Value2"},
                    {"Column1": "Value3", "Column2": "Value4"}
                ]
            },
            {
                "columns": ["ColumnA", "ColumnB"],
                "rows": [
                    {"ColumnA": "Value5", "ColumnB": "Value6"}
                ]
            }
        ]
    }

    print("Actual Response:", response.json())
    print("Expected Response:", expected_response)

    assert response.status_code == 200
    assert response.json() == expected_response



def test_get_data_genie_metrics_db_connection_failure(mocker):
    # Mock database connection failure
    mocker.patch("main.get_db_connection", return_value=None)

    # Make the request
    response = client.get("/getdashboarddata")

    # Assertions
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Database connection failed."
    }


def test_get_data_genie_metrics_execution_error(mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection

    # Mock database behavior to raise an exception
    mock_cursor.execute.side_effect = Exception("Stored procedure execution failed")

    # Make the request
    response = client.get("/getdashboarddata")

    # Assertions
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Failed to execute stored procedure."
    }


def test_get_data_genie_metrics_empty_result_sets(mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection

    # Fix: don't use None, just an empty list
    mock_cursor.description = []
    mock_cursor.fetchall.return_value = []
    mock_cursor.nextset.return_value = False

    response = client.get("/getdashboarddata")

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "result_sets": [
            {
                "columns": [],
                "rows": []
            }
        ]
    }
