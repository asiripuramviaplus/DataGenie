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


def test_get_ticket_status_success(mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection

    # Mock database behavior
    mock_cursor.fetchone.return_value = (1, "TICKET123", "Open", "John Doe", "2023-10-01")
    mock_cursor.description = [("TicketId",), ("TicketNumber",), ("Status",), ("ResolvedBy",), ("ResolutionDate",)]

    # Make the request
    response = client.get("/get-ticket-status?ticket_number=TICKET123")

    # Assertions
    assert response.status_code == 200
    assert response.json() == {
        "TicketId": 1,
        "TicketNumber": "TICKET123",
        "Status": "Open",
        "ResolvedBy": "John Doe",
        "ResolutionDate": "2023-10-01"
    }


def test_get_ticket_status_not_found(mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection

    # Mock database behavior
    mock_cursor.fetchone.return_value = None

    # Make the request
    response = client.get("/get-ticket-status?ticket_number=INVALID_TICKET")

    # Assertions
    assert response.status_code == 200
    assert response.json() == {
        "status": "not_found",
        "message": "Ticket not found."
    }


def test_get_ticket_status_db_connection_failure(mocker):
    # Mock database connection failure
    mocker.patch("main.get_db_connection", return_value=None)

    # Make the request
    response = client.get("/get-ticket-status?ticket_number=TICKET123")

    # Assertions
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Database connection failed."
    }


def test_get_ticket_status_query_execution_error(mock_db_connection):
    mock_conn, mock_cursor = mock_db_connection

    # Mock database behavior
    mock_cursor.execute.side_effect = Exception("Query execution failed")

    # Make the request
    response = client.get("/get-ticket-status?ticket_number=TICKET123")

    # Assertions
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Failed to retrieve ticket status."
    }