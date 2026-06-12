"""Visible tests - authentication still works, plaintext storage does not."""
import pytest
from starter.user_store import get_stored_credential, register, reset, verify


@pytest.fixture(autouse=True)
def clean_store():
    reset()
    yield
    reset()


def test_register_and_verify():
    register("alice", "hunter2!")
    assert verify("alice", "hunter2!") is True


def test_wrong_password_rejected():
    register("alice", "hunter2!")
    assert verify("alice", "not-the-password") is False


def test_password_not_stored_in_plaintext():
    register("alice", "hunter2!")
    stored = get_stored_credential("alice")
    assert "hunter2!" not in stored, "plaintext password found in the store"


def test_stored_credential_is_bcrypt():
    register("alice", "hunter2!")
    assert get_stored_credential("alice").startswith("$2"), "expected a bcrypt hash"
