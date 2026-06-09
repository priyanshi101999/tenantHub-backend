import re
from pydantic import BaseModel, field_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_PATTERN.match(value):
        raise ValueError("Invalid email format")
    return value

def require_phone(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Phone is required")
    return value

class EmailValidatedModel(BaseModel):
    @field_validator("email", check_fields=False)
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

class PhoneRequiredModel(BaseModel):
    @field_validator("phone", check_fields=False)
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return require_phone(value)

class Register(EmailValidatedModel, PhoneRequiredModel):
    name: str
    email: str
    password: str
    role: str
    workspaceName: str
    phone: str

class EmailInput(EmailValidatedModel):
    email: str

class OTPInput(EmailValidatedModel):
    email: str
    code: str

class ResetPassword(EmailValidatedModel):
    new_password: str
    code: str
    email: str

class LoginInput(EmailValidatedModel):
    email: str
    password: str

class RefreshToken(BaseModel):
    refresh_token: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class SetPasswordInput(BaseModel):
    password: str
    secret_token: str

class LoginOut(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    user: dict

class LogoutInput(BaseModel):
    refresh_token: str
    device_id: str

class FCMTokenInput(BaseModel):
    fcm_token: str
    device_id: str

class PhoneInput(PhoneRequiredModel):
    phone: str

class VerifyPhoneInput(PhoneRequiredModel):
    phone: str
    code: str
