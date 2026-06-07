import pytest
from fastapi import status

from app.api.v1.endpoints import task
from app.schemas.response_schema import APIResponse


def test_create_task_endpoint(api_client, monkeypatch):
    async def service(data, db, current_user):
        return APIResponse(
            status=status.HTTP_201_CREATED,
            message="Task created successfully",
            data={"title": data.title, "workspace_id": current_user.workspace_id},
        )

    monkeypatch.setattr(task, "create_task_service", service)

    response = api_client.post(
        "/api/v1/task/create",
        json={"title": "Fix sink", "description": "Kitchen sink leaks"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == "Task created successfully"
    assert response.json()["data"] == {"title": "Fix sink", "workspace_id": 99}


@pytest.mark.parametrize(
    ("method", "path", "service_name", "expected_message"),
    [
        ("patch", "/api/v1/task/update?id=1", "update_task_service", "Task updated successfully"),
        ("get", "/api/v1/task/list?page=1&size=10", "get_task_list__service", "Tasks retrieved successfully"),
        ("get", "/api/v1/task/analytics", "get_analytics_service", "Analytics retrieved successfully"),
        ("get", "/api/v1/task/?id=1", "get_task_service", "Task retrieved successfully"),
    ],
)
def test_task_endpoints(api_client, monkeypatch, method, path, service_name, expected_message):
    async def service(*args, **kwargs):
        return APIResponse(status=status.HTTP_200_OK, message=expected_message, data={"ok": True})

    monkeypatch.setattr(task, service_name, service)

    request = getattr(api_client, method)
    if method == "patch":
        response = request(path, json={"title": "Updated task"})
    else:
        response = request(path)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == expected_message


def test_task_create_endpoint_validates_body(api_client):
    response = api_client.post("/api/v1/task/create", json={"description": "Missing title"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
