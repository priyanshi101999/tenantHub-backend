import pytest
from fastapi import status

from app.api.v1.endpoints import auth
from app.schemas.response_schema import APIResponse


@pytest.mark.parametrize(
    ("path", "payload", "service_name", "expected_message", "expected_status"),
    [
        (
            "/api/v1/auth/register",
            {
                "name": "Priya",
                "email": "priya@example.com",
                "password": "secret",
                "role": "USER",
                "workspaceName": "TenantHub",
                "phone": "9999999999",
            },
            "register_user_service",
            "Registered successfully",
            status.HTTP_201_CREATED,
        ),
        (
            "/api/v1/auth/login",
            {"email": "priya@example.com", "password": "secret"},
            "login_service",
            "Login successful",
            status.HTTP_200_OK,
        ),
        (
            "/api/v1/auth/refresh-token",
            {"refresh_token": "refresh-token"},
            "refresh_token_service",
            "Token refreshed successfully",
            status.HTTP_200_OK,
        ),
    ],
)
def test_auth_post_endpoints(api_client, monkeypatch, path, payload, service_name, expected_message, expected_status):
    async def service(*args, **kwargs):
        return APIResponse(status=status.HTTP_200_OK, message=expected_message, data={"ok": True})

    monkeypatch.setattr(auth, service_name, service)

    response = api_client.post(path, json=payload)

    assert response.status_code == expected_status
    assert response.json()["message"] == expected_message
    assert response.json()["data"] == {"ok": True}


def test_change_password_endpoint_uses_current_user(api_client, monkeypatch, current_user):
    seen = {}

    async def service(data, db, service_current_user):
        seen["current_user"] = service_current_user
        return APIResponse(status=status.HTTP_200_OK, message="Password changed successfully")

    monkeypatch.setattr(auth, "change_password_service", service)

    response = api_client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "old", "new_password": "new"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Password changed successfully"
    assert seen["current_user"] is current_user


def test_send_otp_endpoint(api_client, monkeypatch):
    async def service(phone):
        return APIResponse(status=status.HTTP_200_OK, message=f"OTP sent to {phone}")

    monkeypatch.setattr(auth, "send_otp_service", service)

    response = api_client.post("/api/v1/auth/send-otp", json={"phone": "9999999999"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "OTP sent to 9999999999"
