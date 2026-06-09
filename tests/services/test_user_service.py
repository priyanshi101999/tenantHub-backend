from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.models.enums import Role
from app.schemas.user_schema import InviteUser, UserInput
from app.services import user_service
from tests.db.fake_db import FakeDB, FakeResult


pytestmark = pytest.mark.anyio


@pytest.fixture
def invite_redis():
    class Redis:
        def __init__(self):
            self.values = {}

        async def set(self, key, value, ex=None):
            self.values[key] = (value, ex)

    return Redis()


async def test_add_user_service_other_workspace(current_user):
    db = FakeDB()
    data = UserInput(
        name="New User",
        email="new@example.com",
        role="USER",
        workspace_id=123,
        phone="8888888888",
    )

    with pytest.raises(HTTPException) as exc_info:
        await user_service.add_user_service(data, db, current_user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "You can only add users to your own workspace"
    assert db.rolled_back is True


async def test_add_user_service_duplicate_email(current_user, user):
    db = FakeDB(FakeResult(first=user))
    data = UserInput(
        name="New User",
        email=user.email,
        role="USER",
        workspace_id=current_user.workspace_id,
        phone="8888888888",
    )

    with pytest.raises(HTTPException) as exc_info:
        await user_service.add_user_service(data, db, current_user)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == "User already exists"
    assert db.rolled_back is True


async def test_invite_user_service_success(monkeypatch, invite_redis, user):
    sent_emails = []
    db = FakeDB(FakeResult(first=user))
    data = InviteUser(email=user.email)

    monkeypatch.setattr(user_service, "redis", invite_redis)
    monkeypatch.setattr(user_service, "generate_invite_token", lambda: "invite-token")
    monkeypatch.setattr(user_service.settings, "frontend_baseurl", "https://tenant.test")
    monkeypatch.setattr(user_service, "dispatch_email", lambda *args: sent_emails.append(args))

    response = await user_service.invite_user_service(data, db)

    assert response.status == status.HTTP_200_OK
    assert response.data.email == user.email
    assert response.data.invite_link == "https://tenant.test/invite/invite-token"
    assert invite_redis.values["invite_token:invite-token"] == (user.email, 86400)
    assert sent_emails[0][0] == user.email


async def test_invite_user_service_user_not_found():
    db = FakeDB(FakeResult(first=None))
    data = InviteUser(email="missing@example.com")

    with pytest.raises(HTTPException) as exc_info:
        await user_service.invite_user_service(data, db)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "User not found"


async def test_user_list_service_success(current_user, user):
    db = FakeDB(FakeResult(all_items=[user]), FakeResult(scalar=1))

    response = await user_service.user_list_service(page=1, size=10, db=db, current_user=current_user)

    assert response.status == status.HTTP_200_OK
    assert response.data["pagination"]["total_items"] == 1
    assert response.data["users"][0].email == user.email


async def test_user_list_service_requires_admin(current_user):
    current_user.role = Role.USER
    db = FakeDB()

    with pytest.raises(HTTPException) as exc_info:
        await user_service.user_list_service(page=1, size=10, db=db, current_user=current_user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "You not have access"


@pytest.mark.parametrize(
    ("existing_user", "expected_status", "expected_detail"),
    [
        (None, status.HTTP_404_NOT_FOUND, "User not found"),
        ("other_workspace", status.HTTP_403_FORBIDDEN, "You can not get user from other workspace"),
    ],
)
async def test_get_user_service_errors(existing_user, expected_status, expected_detail, current_user, user):
    if existing_user == "other_workspace":
        user.workspace_id = 123
        result_user = user
    else:
        result_user = None

    db = FakeDB(FakeResult(first=result_user))

    with pytest.raises(HTTPException) as exc_info:
        await user_service.get_user_service(1, db, current_user)

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail
    assert db.rolled_back is True


async def test_get_user_service_success(current_user, user):
    db = FakeDB(FakeResult(first=user))

    response = await user_service.get_user_service(user.id, db, current_user)

    assert response.status == status.HTTP_200_OK
    assert response.data.email == user.email
    assert response.data.workspace_id == current_user.workspace_id
