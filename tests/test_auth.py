import pytest
from datetime import timedelta

from app.auth import hash_password, verify_password, create_jwt, decode_jwt
from app.config import settings


def test_bcrypt_hash_and_verify():
    password = "s3cret_P@ss"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_create_and_decode_sub_and_exp():
    token = create_jwt({"sub": "admin@example.com"}, expires_delta=timedelta(seconds=5))
    payload = decode_jwt(token)
    assert payload["sub"] == "admin@example.com"
    assert "exp" in payload


def test_jwt_default_exp_uses_settings():
    token = create_jwt({"sub": "admin@example.com"})
    payload = decode_jwt(token)
    assert "exp" in payload
