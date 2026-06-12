"""Hidden edge cases."""
import pytest
from starter.user_store import get_stored_credential, register, reset, verify


@pytest.fixture(autouse=True)
def clean_store():
    reset()
    yield
    reset()


def test_same_password_different_hashes():
    register("alice", "shared-password")
    register("bob", "shared-password")
    assert get_stored_credential("alice") != get_stored_credential("bob"), (
        "hashes must be salted"
    )


def test_unknown_user_rejected():
    assert verify("ghost", "anything") is False
