from unittest.mock import patch
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


# Add the parent directory of `main.py` to the Python path
from main import app


client = TestClient(app)  # Initialize the TestClient for testing FastAPI routes

def test_fetch_ticket_details_success():
    """Test successful retrieval of ticket details."""
    with patch("main.SQLAuditLogger") as MockAuditLogger:
        # Mock the `fetch_ticket_details` method to return sample ticket details
        mock_logger = MockAuditLogger.return_value
        mock_logger.fetch_ticket_details.return_value = [
            {"ticket_id": 1, "status": "Open", "created_at": "2023-10-01T12:00:00"},
            {"ticket_id": 2, "status": "Closed", "created_at": "2023-10-02T14:30:00"},
        ]

        # Make a GET request to the endpoint
        response = client.get("/fetch-ticket-details")

        # Assert the response status code and data
        assert response.status_code == 200
        assert response.json() == [
            {"ticket_id": 1, "status": "Open", "created_at": "2023-10-01T12:00:00"},
            {"ticket_id": 2, "status": "Closed", "created_at": "2023-10-02T14:30:00"},
        ]

def test_fetch_ticket_details_empty():
    """Test when no ticket details are available."""
    with patch("main.SQLAuditLogger") as MockAuditLogger:
        # Mock the `fetch_ticket_details` method to return an empty list
        mock_logger = MockAuditLogger.return_value
        mock_logger.fetch_ticket_details.return_value = []

        # Make a GET request to the endpoint
        response = client.get("/fetch-ticket-details")

        # Assert the response status code and data
        assert response.status_code == 200
        assert response.json() == []  # Expect an empty list

def test_fetch_ticket_details_failure():
    """Test when an exception occurs while fetching ticket details."""
    with patch("main.SQLAuditLogger") as MockAuditLogger:
        # Mock the `fetch_ticket_details` method to raise an exception
        mock_logger = MockAuditLogger.return_value
        mock_logger.fetch_ticket_details.side_effect = Exception("Unexpected error occurred")

        # Make a GET request to the endpoint
        response = client.get("/fetch-ticket-details")

        # Debugging: Print the response
        print("Response status code:", response.status_code)
        print("Response JSON:", response.json())

        # Assert the response status code and error message
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal Server Error"}