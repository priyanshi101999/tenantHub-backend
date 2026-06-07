import pytest
from fastapi import status

from app.api.v1.endpoints import user
from app.schemas.response_schema import APIResponse


def test_create_user_endpoint(api_client, monkeypatch):
    async def service(data, db, current_user):
        return APIResponse(
            status=status.HTTP_201_CREATED,
            message="User added successfully",
            data={"email": data.email, "workspace_id": current_user.workspace_id},
        )

    monkeypatch.setattr(user, "add_user_service", service)

    response = api_client.post(
        "/api/v1/user/create",
        json={
            "name": "New User",
            "email": "new@example.com",
            "role": "USER",
            "workspace_id": 99,
            "phone": "8888888888",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == "User added successfully"
    assert response.json()["data"] == {"email": "new@example.com", "workspace_id": 99}


@pytest.mark.parametrize(
    ("method", "path", "service_name", "expected_message", "expected_status"),
    [
        ("post", "/api/v1/user/invite", "invite_user_service", "Invite sent successfully", status.HTTP_201_CREATED),
        ("get", "/api/v1/user/list?page=1&size=10", "user_list_service", "User List fetched successfully", status.HTTP_200_OK),
        ("get", "/api/v1/user/?id=10", "get_user_service", "User fetched successfully", status.HTTP_200_OK),
        ("delete", "/api/v1/user/?id=10", "delete_user_service", "User deleted successfully", status.HTTP_200_OK),
    ],
)
def test_user_endpoints(api_client, monkeypatch, method, path, service_name, expected_message, expected_status):
    async def service(*args, **kwargs):
        return APIResponse(status=status.HTTP_200_OK, message=expected_message, data={"ok": True})

    monkeypatch.setattr(user, service_name, service)

    request = getattr(api_client, method)
    if method == "post":
        response = request(path, json={"email": "new@example.com"})
    else:
        response = request(path)

    assert response.status_code == expected_status
    assert response.json()["message"] == expected_message


def test_user_create_endpoint_validates_body(api_client):
    response = api_client.post("/api/v1/user/create", json={"email": "bad@example.com"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
