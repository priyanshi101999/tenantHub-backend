from types import ModuleType, SimpleNamespace
from datetime import datetime, timezone
import sys

import pytest

from app.models.enums import Role
from app.models.plan import Plan
from app.models.user import User
from app.models.workspace import Workspace


notification_task_stub = ModuleType("app.tasks.notification_task")
notification_task_stub.send_notification_task = SimpleNamespace(delay=lambda *args, **kwargs: None)
sys.modules["app.tasks.notification_task"] = notification_task_stub

email_task_stub = ModuleType("app.tasks.email_task")
email_task_stub.send_email_task = SimpleNamespace(delay=lambda *args, **kwargs: None)
sys.modules["app.tasks.email_task"] = email_task_stub


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def current_user():
    return SimpleNamespace(
        id=10,
        workspace_id=99,
        role=Role.ADMIN,
        workspace=SimpleNamespace(plan_id=1),
    )


@pytest.fixture
def workspace():
    return Workspace(id=99, name="Main Workspace", owner_id=10)


@pytest.fixture
def user(workspace):
    return User(
        id=10,
        name="Priya",
        email="priya@example.com",
        phone="9999999999",
        password="hashed-password",
        role=Role.USER,
        email_verified=True,
        phone_verified=False,
        workspace_id=workspace.id,
        workspace=workspace,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def free_plan():
    return Plan(
        id=1,
        name="FREE",
        price=0,
        stripe_price_id="price_test",
        max_tasks=20,
        max_users=5,
    )


from tests.db.session import Session, client, db_session, test_database_url, test_engine  # noqa: E402,F401
