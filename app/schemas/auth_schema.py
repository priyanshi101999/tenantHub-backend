from pydantic import BaseModel

class Register(BaseModel):
    name: str
    email: str
    password: str
    role: str
    workspaceName: str
    phone: str

class EmailInput(BaseModel):
    email: str

class OTPInput(BaseModel):
    email: str
    code: str

class ResetPassword(OTPInput):
    new_password: str

class LoginInput(BaseModel):
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