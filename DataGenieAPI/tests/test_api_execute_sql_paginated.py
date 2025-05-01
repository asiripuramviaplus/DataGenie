# import pytest
# from fastapi.testclient import TestClient  # Import the FastAPI TestClient
# from unittest.mock import MagicMock, patch
# import sys
# import os

# # Add the parent directory of `main.py` to the Python path
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))  # Import your FastAPI app

# # Import the FastAPI app instance
# from main import app

# # Ensure that `execute_query` is properly mocked
# @pytest.mark.asyncio
# async def test_api_execute_sql_paginated_success(mocker):
#     """
#     Test the successful execution of a paginated SQL query.
#     """
#     # Mock the database connection to return a MagicMock object
#     mock_connection = MagicMock()
#     mocker.patch("main.get_db_connection", return_value=mock_connection)
    
#     # Mock the execute_query function to return a valid response
#     mocker.patch("main.execute_query", return_value={
#         "columns": ["id", "name"],
#         "rows": [[1, "Test"]],
#         "message": "Query executed successfully",
#         "message_code": "SUCCESS",
#         "execution_time": "0.01 seconds",
#         "query_status": "SUCCESS",
#         "row_count": 1,
#         "data_size_mb": 0.001,
#         "total_records": 1,
#         "executed_sql": "SELECT * FROM test_table"
#     })

#     request_payload = {"sql_query": "SELECT * FROM test_table"}

#     with TestClient(app) as client:
#         response = client.post("/execute-sql-paginated?offset=100&fetch=10", json=request_payload)

#     # Check if we receive status 200 and expected response
#     assert response.status_code == 200
#     response_json = response.json()
#     assert response_json["columns"] == ["id", "name"]
#     assert response_json["rows"] == [[1, "Test"]]
#     assert response_json["message"] == "Query executed successfully"
#     assert response_json["total_records"] == 1

# @pytest.mark.asyncio
# async def test_api_execute_sql_paginated_invalid_query(mocker):
#     """
#     Test the case where the SQL query is invalid.
#     """
#     # Mocking an invalid query scenario
#     mock_connection = MagicMock()
#     mocker.patch("main.get_db_connection", return_value=mock_connection)
#     mocker.patch("main.execute_query", side_effect=Exception("Invalid SQL query"))

#     request_payload = {"sql_query": "INVALID SQL QUERY"}

#     # Use FastAPI's TestClient instead of AsyncClient
#     with TestClient(app) as client:
#         response = client.post("/execute-sql-paginated?offset=0&fetch=10", json=request_payload)

#     assert response.status_code == 400  # Changed to 400 since it's an invalid SQL query
#     assert response.json() == {"detail": "Invalid SQL query"}



# @pytest.mark.asyncio
# async def test_api_execute_sql_paginated_db_connection_failure(mocker):
#     """
#     Test the case where the database connection fails.
#     """
#     mocker.patch("main.get_db_connection", return_value=None)

#     request_payload = {"sql_query": "SELECT * FROM test_table"}

#     # Use FastAPI's TestClient instead of AsyncClient
#     with TestClient(app) as client:
#         response = client.post("/execute-sql-paginated?offset=0&fetch=10", json=request_payload)

#     assert response.status_code == 500
#     assert response.json() == {"detail": "Database connection failed."}

# @pytest.mark.asyncio
# async def test_api_execute_sql_paginated_invalid_query(mocker):
#     """
#     Test the case where the SQL query is invalid.
#     """
#     mocker.patch("main.get_db_connection", return_value="mock_connection")
#     mocker.patch("main.execute_query", side_effect=Exception("Invalid SQL query"))

#     request_payload = {"sql_query": "INVALID SQL QUERY"}

#     # Use FastAPI's TestClient instead of AsyncClient
#     with TestClient(app) as client:
#         response = client.post("/execute-sql-paginated?offset=0&fetch=10", json=request_payload)

#     assert response.status_code == 400  # Changed to 400 since it's an invalid SQL query
#     assert response.json() == {"detail": "Invalid SQL query"}

# @pytest.mark.asyncio
# async def test_api_execute_sql_paginated_empty_query_result(mocker):
#     """
#     Test the case where the SQL query returns no results.
#     """
#     mock_connection = MagicMock()
#     mocker.patch("main.get_db_connection", return_value=mock_connection)
#     mocker.patch("main.execute_query", return_value={
#         "columns": [],
#         "rows": [],
#         "message": "No data found",
#         "message_code": "NO_DATA",
#         "execution_time": "0.01 seconds",
#         "query_status": "SUCCESS",
#         "row_count": 0,
#         "data_size_mb": 0.0,
#         "total_records": 0,
#         "executed_sql": "SELECT * FROM empty_table"
#     })

#     request_payload = {"sql_query": "SELECT * FROM empty_table"}

#     with TestClient(app) as client:
#         response = client.post("/execute-sql-paginated?offset=0&fetch=10", json=request_payload)

#     assert response.status_code == 200
#     response_json = response.json()
#     assert response_json["columns"] == []
#     assert response_json["rows"] == []
#     assert response_json["message"] == "No data found"
#     assert response_json["total_records"] == 0

# @pytest.mark.asyncio
# async def test_api_execute_sql_paginated_offset_greater_than_total_records(mocker):
#     """
#     Test the case where the offset is greater than the total number of records.
#     """
#     mocker.patch("main.get_db_connection", return_value="mock_connection")
#     mocker.patch("main.execute_query", return_value={
#         "columns": [],
#         "rows": [],
#         "message": "No data found",
#         "message_code": "NO_DATA",
#         "execution_time": "0.01 seconds",
#         "query_status": "SUCCESS",
#         "row_count": 0,
#         "data_size_mb": 0.0,
#         "total_records": 1,
#         "executed_sql": "SELECT * FROM test_table"
#     })

#     request_payload = {"sql_query": "SELECT * FROM test_table"}

#     with TestClient(app) as client:
#         response = client.post("/execute-sql-paginated?offset=100&fetch=10", json=request_payload)

#     assert response.status_code == 200
#     response_json = response.json()
#     assert response_json["columns"] == []
#     assert response_json["rows"] == []
#     assert response_json["message"] == "No data found"
#     assert response_json["total_records"] == 1



import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

import sys
import os

# Fix Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Adjust this if your app is in a different folder
from main import app
from fastapi import HTTPException





def test_api_execute_sql_paginated_success(mocker):
    mock_conn = MagicMock()
    mocker.patch("main.get_db_connection", return_value=mock_conn)

    mocker.patch("main.execute_query", side_effect=[
        {
            "total_records": 1,
            "columns": ["id", "name"],
            "rows": [[1, "Test"]],
            "message": "Success",
            "message_code": "SUCCESS",
            "execution_time": "0.01 seconds",
            "query_status": "SUCCESS",
            "row_count": 1,
            "data_size_mb": 0.01,
            "executed_sql": "SELECT * FROM test"
        },
        {
            "total_records": 1,
            "columns": ["id", "name"],
            "rows": [[1, "Test"]],
            "message": "Success",
            "message_code": "SUCCESS",
            "execution_time": "0.01 seconds",
            "query_status": "SUCCESS",
            "row_count": 1,
            "data_size_mb": 0.01,
            "executed_sql": "SELECT * FROM test"
        }
    ])

    client = TestClient(app)
    response = client.post("/execute-sql-paginated?offset=0&fetch=10", json={"sql_query": "SELECT * FROM test"})

    assert response.status_code == 200
    data = response.json()
    assert data["rows"] == [{"id": 1, "name": "Test"}]
    assert data["message_code"] == 1


def test_api_execute_sql_paginated_invalid_query(mocker):
    mock_conn = MagicMock()
    mocker.patch("main.get_db_connection", return_value=mock_conn)
    mocker.patch("main.execute_query", return_value={"error": "Syntax error"})

    client = TestClient(app)
    response = client.post("/execute-sql-paginated", json={"sql_query": "BAD SQL"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid SQL query"


def test_api_execute_sql_paginated_db_connection_failure(mocker):
    mocker.patch("main.get_db_connection", return_value=None)

    client = TestClient(app)
    response = client.post("/execute-sql-paginated", json={"sql_query": "SELECT * FROM test"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Database connection failed."

def test_api_execute_sql_paginated_offset_exceeds_total(mocker):
    mock_conn = MagicMock()
    mocker.patch("main.get_db_connection", return_value=mock_conn)

    mocker.patch("main.execute_query", side_effect=[
        {
            "total_records": 2,
            "columns": ["id", "name"],
            "rows": [[1, "Test1"], [2, "Test2"]],
            "message": "Success",
            "message_code": "SUCCESS",
            "execution_time": "0.01 seconds",
            "query_status": "SUCCESS",
            "row_count": 2,
            "data_size_mb": 0.02,
            "executed_sql": "SELECT * FROM test"
        },
        {
            "total_records": 2,
            "columns": ["id", "name"],
            "rows": [],
            "message": "No data found",
            "message_code": "NO_DATA",
            "execution_time": "0.01 seconds",
            "query_status": "SUCCESS",
            "row_count": 0,
            "data_size_mb": 0.0,
            "executed_sql": "SELECT * FROM test"
        }
    ])

    client = TestClient(app)
    response = client.post("/execute-sql-paginated?offset=10&fetch=10", json={"sql_query": "SELECT * FROM test"})

    assert response.status_code == 200
    data = response.json()
    assert data["rows"] == []
    assert data["message_code"] == 0

def test_api_execute_sql_paginated_fetch_total_records_exception(mocker):
    mock_conn = MagicMock()
    mocker.patch("main.get_db_connection", return_value=mock_conn)
    mocker.patch("main.execute_query", side_effect=Exception("Database crashed"))

    client = TestClient(app)
    response = client.post("/execute-sql-paginated", json={"sql_query": "SELECT * FROM test"})

    assert response.status_code == 500
    assert "Failed to fetch total records from DB" in response.json()["detail"]
