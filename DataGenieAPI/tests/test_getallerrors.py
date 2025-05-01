from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory of `main.py` to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from main import app


client = TestClient(app)  # Initialize the TestClient for testing FastAPI routes

def test_get_all_errors_success():
    """Test successful retrieval of error logs."""
    with patch("main.SQLAuditLogger") as MockAuditLogger:
        # Mock the `get_all_errors` method to return sample error logs
        mock_logger = MockAuditLogger.return_value
        mock_logger.get_all_errors.return_value = [
            {"error_id": 1, "message": "Database connection failed", "timestamp": "2023-10-01T12:00:00"},
            {"error_id": 2, "message": "Invalid SQL syntax", "timestamp": "2023-10-02T14:30:00"},
        ]

        # Make a GET request to the endpoint
        response = client.get("/get-all-errors")

        # Assert the response status code and data
        assert response.status_code == 200
        assert response.json() == [
            {"error_id": 1, "message": "Database connection failed", "timestamp": "2023-10-01T12:00:00"},
            {"error_id": 2, "message": "Invalid SQL syntax", "timestamp": "2023-10-02T14:30:00"},
        ]

def test_get_all_errors_empty():
    """Test when no error logs are available."""
    with patch("main.SQLAuditLogger") as MockAuditLogger:
        # Mock the `get_all_errors` method to return an empty list
        mock_logger = MockAuditLogger.return_value
        mock_logger.get_all_errors.return_value = []

        # Make a GET request to the endpoint
        response = client.get("/get-all-errors")

        # Assert the response status code and data
        assert response.status_code == 200
        assert response.json() == []  # Expect an empty list

def test_get_all_errors_failure():
    """Test when an exception occurs while fetching error logs."""
    with patch("main.SQLAuditLogger") as MockAuditLogger:
        # Mock the `get_all_errors` method to raise an exception
        mock_logger = MockAuditLogger.return_value
        mock_logger.get_all_errors.side_effect = Exception("Unexpected error occurred")

        # Make a GET request to the endpoint
        response = client.get("/get-all-errors")



        # Assert the response status code and error message
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal Server Error"}

