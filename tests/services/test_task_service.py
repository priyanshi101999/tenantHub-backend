from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from app.models.enums import Priority, TaskStatus
from app.models.task import Task
from app.schemas.task_schema import TaskInput, TaskUpdate
from app.services import task_service
from tests.db.fake_db import FakeDB, FakeResult


pytestmark = pytest.mark.anyio


@pytest.fixture
def task():
    return Task(
        id=1,
        workspace_id=99,
        title="Fix sink",
        description="Kitchen sink leaks",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by=10,
        assignee_id=None,
        due_date=None,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def pdf_file():
    return SimpleNamespace(
        filename="invoice.pdf",
        content_type="application/pdf",
        file=BytesIO(b"pdf-bytes"),
    )


@pytest.mark.parametrize(
    ("plan_exists", "task_count", "expected_status", "expected_detail"),
    [
        (False, None, status.HTTP_404_NOT_FOUND, "Plan not found"),
        (True, 21, status.HTTP_403_FORBIDDEN, "You have reached the maximum number of tasks for this plan"),
    ],
)
async def test_check_plan_errors(plan_exists, task_count, expected_status, expected_detail, free_plan, current_user):
    db_results = [FakeResult(first=free_plan if plan_exists else None)]

    if task_count is not None:
        db_results.append(FakeResult(scalar=task_count))

    db = FakeDB(*db_results)

    with pytest.raises(HTTPException) as exc_info:
        await task_service.check_plan(1, db, current_user)

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail


async def test_check_plan_success(free_plan, current_user):
    db = FakeDB(FakeResult(first=free_plan), FakeResult(scalar=5))

    result = await task_service.check_plan(1, db, current_user)

    assert result is True


async def test_create_task_service_success(free_plan, current_user):
    created_task = Task(
        id=1,
        workspace_id=current_user.workspace_id,
        title="Replace filter",
        description="HVAC filter",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by=current_user.id,
        assignee_id=None,
        due_date=None,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    created_task.attachments = []
    db = FakeDB(FakeResult(first=free_plan), FakeResult(scalar=0), FakeResult(first=created_task))
    data = TaskInput(title="Replace filter", description="HVAC filter")

    response = await task_service.create_task_service(data, db, current_user)

    assert response.status == status.HTTP_201_CREATED
    assert response.data.title == "Replace filter"
    assert response.data.created_by == current_user.id
    assert response.data.workspace_id == current_user.workspace_id
    assert db.committed is True


async def test_create_task_service_assignee_not_found(free_plan, current_user):
    db = FakeDB(
        FakeResult(first=free_plan),
        FakeResult(scalar=0),
        FakeResult(first=None),
    )
    data = TaskInput(title="Paint door", assignee_id=123)

    with pytest.raises(HTTPException) as exc_info:
        await task_service.create_task_service(data, db, current_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Assignee not found in your workspace"


async def test_update_task_service_success(task, current_user):
    db = FakeDB(FakeResult(first=task), FakeResult(first=task))
    data = TaskUpdate(title="New title", assignee_id=None, status=TaskStatus.TODO)

    response = await task_service.update_task_service(1, data, db, current_user)

    assert response.status == status.HTTP_200_OK
    assert response.data.title == "New title"
    assert db.committed is True


async def test_update_task_service_other_workspace(task, current_user):
    task.workspace_id = 100
    db = FakeDB(FakeResult(first=task))
    data = TaskUpdate(title="New title", assignee_id=None, status=None)

    with pytest.raises(HTTPException) as exc_info:
        await task_service.update_task_service(1, data, db, current_user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "You can not update task from other workspace"
    assert db.rolled_back is True


@pytest.mark.parametrize(
    ("task_exists", "expected_status"),
    [
        (True, status.HTTP_200_OK),
        (False, status.HTTP_404_NOT_FOUND),
    ],
)
async def test_get_task_service(task_exists, expected_status, task, current_user):
    db = FakeDB(FakeResult(first=task if task_exists else None))

    if expected_status == status.HTTP_404_NOT_FOUND:
        with pytest.raises(HTTPException) as exc_info:
            await task_service.get_task_service(1, db, current_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Task not found"
        return

    response = await task_service.get_task_service(1, db, current_user)

    assert response.status == status.HTTP_200_OK
    assert response.data.id == task.id
    assert response.data.title == task.title


async def test_get_analytics_service_success(current_user):
    analytics = SimpleNamespace(total=0, todo=None, in_progress=None, done=None, overdue=None)
    db = FakeDB(FakeResult(first=analytics))

    response = await task_service.get_analytics_service(db, current_user)

    assert response.status == status.HTTP_200_OK
    assert response.data == {
        "total_tasks": 0,
        "todo": 0,
        "in_progress": 0,
        "done": 0,
        "overdue": 0,
    }
    query = str(db.executed[0])
    assert "tasks.due_date <" in query
    assert "tasks.status !=" in query


async def test_mark_overdue_tasks_service_updates_matching_tasks():
    db = FakeDB(FakeResult(rowcount=2))

    updated_count = await task_service.mark_overdue_tasks_service(db)

    assert updated_count == 2
    assert db.committed is True


async def test_apply_overdue_status_marks_past_due_task(task):
    task.due_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

    task_service.apply_overdue_status(task)

    assert task.status == TaskStatus.OVERDUE


async def test_apply_overdue_status_keeps_done_task_done(task):
    task.status = TaskStatus.DONE
    task.due_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

    task_service.apply_overdue_status(task)

    assert task.status == TaskStatus.DONE


async def test_attach_file_service_success(tmp_path, monkeypatch, task, current_user, pdf_file):
    monkeypatch.chdir(tmp_path)
    pro_plan = SimpleNamespace(name="PRO")
    db = FakeDB(FakeResult(first=task), FakeResult(first=pro_plan))

    response = await task_service.attach_file_Service(1, pdf_file, db, current_user)

    assert response.status == status.HTTP_200_OK
    assert response.data.file_name == "invoice.pdf"
    assert (tmp_path / "uploads" / "99" / "1" / "invoice.pdf").read_bytes() == b"pdf-bytes"
    assert db.committed is True


@pytest.mark.parametrize(
    ("content_type", "expected_detail"),
    [
        ("application/x-msdownload", "File type not allowed"),
        ("text/plain", "File type not allowed"),
    ],
)
async def test_attach_file_service_invalid_type(content_type, expected_detail, tmp_path, monkeypatch, task, current_user):
    monkeypatch.chdir(tmp_path)
    db = FakeDB(FakeResult(first=task))
    upload = SimpleNamespace(
        filename="bad-file.txt",
        content_type=content_type,
        file=BytesIO(b"bad"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await task_service.attach_file_Service(1, upload, db, current_user)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail == expected_detail
    assert db.rolled_back is True
