import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import status
import sys
import os

# Fix Python path to import main app and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app, TicketUpdateRequest  # Adjust if your app is in a subfolder

# -------------------------------
# Fixtures
# -------------------------------

@pytest.fixture
def mock_db_connection(mocker):
    """Mock the DB connection and cursor."""
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    mock_conn.cursor.return_value = mock_cursor
    mocker.patch("main.get_db_connection", return_value=mock_conn)
    return mock_conn, mock_cursor

@pytest.fixture
def mock_broadcast(mocker):
    return mocker.patch("main.manager.broadcast", return_value=None)

@pytest_asyncio.fixture
async def async_client():
    """Provides an async HTTP client using FastAPI's ASGI transport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# -------------------------------
# Test Cases
# -------------------------------

@pytest.mark.asyncio
async def test_update_ticket_status_assigned_success(async_client, mock_db_connection, mock_broadcast):
    conn, cursor = mock_db_connection
    payload = {
        "ticket_number": "T123",
        "status": "assigned",
        "resolved_by": "Agent001"
    }

    response = await async_client.post("/update-ticket-status", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Ticket updated successfully."
    cursor.execute.assert_called_once()
    mock_broadcast.assert_called_with("Ticket number: T123 is assigned to Agent001.")


@pytest.mark.asyncio
async def test_update_ticket_status_resolved_success(async_client, mock_db_connection, mock_broadcast):
    payload = {
        "ticket_number": "T124",
        "status": "resolved",
        "resolved_by": "Agent002"
    }

    response = await async_client.post("/update-ticket-status", json=payload)

    assert response.status_code == status.HTTP_200_OK
    mock_broadcast.assert_called_with("Ticket number: T124 was resolved by Agent002.")


@pytest.mark.asyncio
async def test_update_ticket_status_unknown_status(async_client, mock_db_connection, mock_broadcast):
    payload = {
        "ticket_number": "T125",
        "status": "pending",
        "resolved_by": "Agent003"
    }

    response = await async_client.post("/update-ticket-status", json=payload)

    assert response.status_code == status.HTTP_200_OK
    mock_broadcast.assert_called_with("Ticket number: T125 updated to status 'pending' by Agent003.")


@pytest.mark.asyncio
async def test_update_ticket_status_db_failure(async_client, mocker):
    mocker.patch("main.get_db_connection", return_value=None)

    payload = {
        "ticket_number": "T126",
        "status": "assigned",
        "resolved_by": "Agent004"
    }

    response = await async_client.post("/update-ticket-status", json=payload)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Database connection failed."


@pytest.mark.asyncio
async def test_update_ticket_status_sql_exception(async_client, mock_db_connection, mocker):
    conn, cursor = mock_db_connection
    cursor.execute.side_effect = Exception("SQL error")

    payload = {
        "ticket_number": "T127",
        "status": "resolved",
        "resolved_by": "Agent005"
    }

    response = await async_client.post("/update-ticket-status", json=payload)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Internal server error."
