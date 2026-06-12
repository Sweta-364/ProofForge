"""Hidden edge cases."""
from fastapi.testclient import TestClient
from starter.main import app

client = TestClient(app)


def test_uppercase_extension_allowed():
    response = client.post(
        "/api/upload", params={"filename": "PHOTO.PNG"}, content=b"bytes"
    )
    assert response.status_code == 200


def test_no_extension_rejected():
    response = client.post(
        "/api/upload", params={"filename": "README"}, content=b"bytes"
    )
    assert response.status_code == 415


def test_empty_body_rejected_with_400():
    response = client.post(
        "/api/upload", params={"filename": "empty.png"}, content=b""
    )
    assert response.status_code == 400


def test_exactly_max_size_allowed():
    response = client.post(
        "/api/upload", params={"filename": "edge.png"}, content=b"x" * (1024 * 1024)
    )
    assert response.status_code == 200
