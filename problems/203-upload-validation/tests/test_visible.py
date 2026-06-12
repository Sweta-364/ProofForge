"""Visible tests - the reported abuse cases."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_valid_image_upload_succeeds():
    response = client.post(
        "/api/upload", params={"filename": "avatar.png"}, content=b"fake-png-bytes"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "stored"


def test_executable_rejected_with_415():
    response = client.post(
        "/api/upload", params={"filename": "malware.exe"}, content=b"MZ..."
    )
    assert response.status_code == 415


def test_oversized_upload_rejected_with_413():
    response = client.post(
        "/api/upload",
        params={"filename": "huge.png"},
        content=b"x" * (2 * 1024 * 1024),
    )
    assert response.status_code == 413
