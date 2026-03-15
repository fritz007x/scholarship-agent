import pytest
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)
from datetime import timedelta


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "SecurePass123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password(self):
        hashed = get_password_hash("CorrectPass123")
        assert not verify_password("WrongPass123", hashed)

    def test_different_hashes(self):
        password = "SamePass123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2  # bcrypt uses random salt


class TestJWTTokens:
    def test_create_and_decode(self):
        token = create_access_token(data={"sub": "42"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(minutes=5)
        )
        payload = decode_access_token(token)
        assert payload is not None

    def test_invalid_token(self):
        payload = decode_access_token("not.a.valid.token")
        assert payload is None

    def test_tampered_token(self):
        token = create_access_token(data={"sub": "1"})
        tampered = token[:-5] + "xxxxx"
        payload = decode_access_token(tampered)
        assert payload is None
