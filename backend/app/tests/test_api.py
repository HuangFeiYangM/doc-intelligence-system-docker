"""
Integration tests for API endpoints.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestDocumentEndpoints:
    """Tests for document upload endpoints."""

    def test_upload_without_file(self, client):
        """Test upload without file."""
        response = client.post("/api/v1/documents/upload")
        assert response.status_code == 422  # Validation error

    def test_upload_invalid_file_type(self, client, tmp_path):
        """Test upload with invalid file type."""
        # Create a text file
        text_file = tmp_path / "test.txt"
        text_file.write_text("This is a test file")

        with open(text_file, "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.txt", f, "text/plain")}
            )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


class TestTemplateEndpoints:
    """Tests for template management endpoints."""

    def test_create_template_invalid_json(self, client):
        """Test creating template with invalid field_mapping JSON."""
        response = client.post(
            "/api/v1/templates",
            data={
                "name": "Test Template",
                "field_mapping": "not valid json",
            }
        )

        assert response.status_code == 400
        assert "Invalid field_mapping JSON" in response.json()["detail"]

    def test_get_nonexistent_template(self, client):
        """Test getting a non-existent template."""
        response = client.get(f"/api/v1/templates/{uuid.uuid4()}")
        assert response.status_code == 404


class TestTaskEndpoints:
    """Tests for task management endpoints."""

    def test_get_nonexistent_task_status(self, client):
        """Test getting status of non-existent task."""
        response = client.get(f"/api/v1/tasks/{uuid.uuid4()}/status")
        assert response.status_code == 404

    def test_get_nonexistent_task_result(self, client):
        """Test getting result of non-existent task."""
        response = client.get(f"/api/v1/tasks/{uuid.uuid4()}/result")
        assert response.status_code == 404


class TestDownloadEndpoints:
    """Tests for file download endpoints."""

    def test_download_nonexistent_task(self, client):
        """Test downloading result for non-existent task."""
        response = client.get(f"/api/v1/download/{uuid.uuid4()}")
        assert response.status_code == 404
