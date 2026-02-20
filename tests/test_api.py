"""Tests for the REST API."""

import pytest
from fastapi.testclient import TestClient

from cee.main import app

client = TestClient(app)


def test_execute_python_success():
    response = client.post(
        "/execute",
        json={"language": "python", "code": 'print("hi")', "timeout": 5},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["stdout"].strip() == "hi"
    assert data["exit_code"] == 0
    assert "job_id" in data


def test_execute_python_error():
    response = client.post(
        "/execute",
        json={"language": "python", "code": "raise SystemExit(1)", "timeout": 5},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "failed"
    assert data["exit_code"] == 1


def test_execute_with_stdin():
    code = "import sys\nprint(sys.stdin.read().strip())"
    response = client.post(
        "/execute",
        json={"language": "python", "code": code, "timeout": 5, "stdin": "test_input"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert data["stdout"].strip() == "test_input"


def test_execute_bash():
    response = client.post(
        "/execute",
        json={"language": "bash", "code": "echo bash_works", "timeout": 5},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "completed"
    assert "bash_works" in data["stdout"]


def test_get_job():
    post_response = client.post(
        "/execute",
        json={"language": "python", "code": 'print("stored")', "timeout": 5},
    )
    assert post_response.status_code == 201
    job_id = post_response.json()["job_id"]

    get_response = client.get(f"/jobs/{job_id}")
    assert get_response.status_code == 200
    assert get_response.json()["job_id"] == job_id
    assert get_response.json()["stdout"].strip() == "stored"


def test_get_job_not_found():
    response = client.get("/jobs/nonexistent-job-id")
    assert response.status_code == 404


def test_invalid_language():
    response = client.post(
        "/execute",
        json={"language": "ruby", "code": "puts 'hi'", "timeout": 5},
    )
    assert response.status_code == 422


def test_timeout_out_of_range():
    response = client.post(
        "/execute",
        json={"language": "python", "code": "pass", "timeout": 0},
    )
    assert response.status_code == 422

    response = client.post(
        "/execute",
        json={"language": "python", "code": "pass", "timeout": 61},
    )
    assert response.status_code == 422
