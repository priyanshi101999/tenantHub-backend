from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.schemas.auth_schema import ChangePassword, LoginInput, OTPInput, RefreshToken
from app.services import auth_service
from tests.db.fake_db import FakeDB, FakeResult


pytestmark = pytest.mark.anyio


@pytest.fixture
def auth_redis():
    class Redis:
        def __init__(self):
            self.values = {}
            self.deleted = []

        async def get(self, key):
            return self.values.get(key)

        async def set(self, key, value, ex=None):
            self.values[key] = value

        async def delete(self, key):
            self.deleted.append(key)

    return Redis()


async def test_login_service_success(monkeypatch, user):
    db = FakeDB(FakeResult(first=user))
    data = LoginInput(email=user.email, password="secret")

    monkeypatch.setattr(auth_service, "verify_password", lambda raw, hashed: True)
    monkeypatch.setattr(auth_service, "create_jwt_token", lambda payload: "access-token")
    monkeypatch.setattr(auth_service, "create_refresh_token", lambda payload: "refresh-token")

    response = await auth_service.login_service(data, db)

    assert response.status == status.HTTP_200_OK
    assert response.data.access_token == "access-token"
    assert response.data.refresh_token == "refresh-token"
    assert response.data.user["email"] == user.email
    assert db.committed is True


@pytest.mark.parametrize(
    ("user_exists", "email_verified", "password_ok", "expected_status", "expected_detail"),
    [
        (False, True, True, status.HTTP_404_NOT_FOUND, "User not found"),
        (True, False, True, status.HTTP_401_UNAUTHORIZED, "Email not verified"),
        (True, True, False, status.HTTP_401_UNAUTHORIZED, "Incorrect password"),
    ],
)
async def test_login_service_errors(
    monkeypatch,
    user,
    user_exists,
    email_verified,
    password_ok,
    expected_status,
    expected_detail,
):
    user.email_verified = email_verified
    db = FakeDB(FakeResult(first=user if user_exists else None))
    data = LoginInput(email=user.email, password="secret")

    monkeypatch.setattr(auth_service, "verify_password", lambda raw, hashed: password_ok)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.login_service(data, db)

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail


async def test_refresh_token_service_success(monkeypatch):
    token = SimpleNamespace(
        user_id=10,
        workspace_id=99,
        expired_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db = FakeDB(FakeResult(first=token))
    data = RefreshToken(refresh_token="refresh-token")

    monkeypatch.setattr(auth_service, "create_jwt_token", lambda payload: "new-access-token")

    response = await auth_service.refresh_token_service(data, db)

    assert response.status == status.HTTP_200_OK
    assert response.data == {"access_token": "new-access-token", "token_type": "Bearer"}


@pytest.mark.parametrize(
    ("token", "expected_detail"),
    [
        (None, "Invalid refresh token"),
        (
            SimpleNamespace(
                user_id=10,
                workspace_id=99,
                expired_at=datetime.now(timezone.utc) - timedelta(days=1),
            ),
            "Expired refresh token",
        ),
    ],
)
async def test_refresh_token_service_errors(token, expected_detail):
    db = FakeDB(FakeResult(first=token))
    data = RefreshToken(refresh_token="refresh-token")

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_token_service(data, db)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == expected_detail


async def test_change_password_service_success(monkeypatch, current_user):
    db = FakeDB()
    current_user.password = "old-hash"
    data = ChangePassword(old_password="old", new_password="new")

    monkeypatch.setattr(auth_service, "verify_password", lambda raw, hashed: True)
    monkeypatch.setattr(auth_service, "hash_password", lambda raw: f"hashed-{raw}")

    response = await auth_service.change_password_service(data, db, current_user)

    assert response.status == status.HTTP_200_OK
    assert current_user.password == "hashed-new"
    assert db.committed is True


async def test_change_password_service_wrong_old_password(monkeypatch, current_user):
    db = FakeDB()
    current_user.password = "old-hash"
    data = ChangePassword(old_password="wrong", new_password="new")

    monkeypatch.setattr(auth_service, "verify_password", lambda raw, hashed: False)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.change_password_service(data, db, current_user)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "Incorrect old password"


async def test_verify_otp_service_success(monkeypatch, auth_redis, user):
    auth_redis.values[f"email_verification:{user.email}"] = "123456"
    db = FakeDB(FakeResult(first=user))
    data = OTPInput(email=user.email, code="123456")

    monkeypatch.setattr(auth_service, "redis", auth_redis)

    response = await auth_service.verify_otp_service(data, db)

    assert response.status == status.HTTP_200_OK
    assert user.email_verified is True
    assert db.committed is True
    assert auth_redis.deleted == [f"email_verification:{user.email}"]


@pytest.mark.parametrize(
    ("stored_otp", "entered_otp", "expected_detail"),
    [
        (None, "123456", "OTP expired"),
        ("111111", "123456", "Invalid OTP"),
    ],
)
async def test_verify_otp_service_errors(monkeypatch, auth_redis, user, stored_otp, entered_otp, expected_detail):
    if stored_otp is not None:
        auth_redis.values[f"email_verification:{user.email}"] = stored_otp

    db = FakeDB()
    data = OTPInput(email=user.email, code=entered_otp)

    monkeypatch.setattr(auth_service, "redis", auth_redis)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.verify_otp_service(data, db)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == expected_detail
