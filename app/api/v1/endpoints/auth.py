from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.auth_schema import ChangePassword
from app.schemas.auth_schema import SetPasswordInput,Register, EmailInput, OTPInput, LoginInput,RefreshToken,ResetPassword
from app.models.user import User
from app.services.auth_service import verify_email_service, verify_otp_service, register_user_service,login_service,refresh_token_service,change_password_service,forgot_password_service,reset_password_service,set_password_service
from app.api.deps import get_current_user
from app.schemas.response_schema import APIResponse
from sqlalchemy.ext.asyncio import AsyncSession

router=APIRouter(prefix="/auth", tags=["Authentication"])

@router.post('/register', status_code=201, response_model=APIResponse)
async def register(registerData: Register, db : AsyncSession = Depends(get_db)):
    return await register_user_service(registerData, db)

@router.post("/verify-email", status_code=200, response_model=APIResponse)
async def verify_email(data: EmailInput):
    return await verify_email_service(data.email)

@router.post("/verify-otp", status_code=200, response_model=APIResponse)
async def verify_otp(otpData:OTPInput, db:AsyncSession=Depends(get_db)):
    return await verify_otp_service(otpData, db)

@router.post("/login", status_code=200, response_model=APIResponse)
async def login(loginData:LoginInput, db:AsyncSession=Depends(get_db)):
    return await login_service(loginData, db)

@router.post("/refresh-token", status_code=200, response_model=APIResponse)
async def refresh_token(data:RefreshToken, db:AsyncSession=Depends(get_db)):
    return await refresh_token_service(data, db)

@router.post("/change-password", status_code=200, response_model=APIResponse)
async def change_password(data:ChangePassword, db:AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    
    return await change_password_service(data, db, current_user)

@router.post("/forgot-password", status_code=200, response_model=APIResponse)
async def forgot_password(data:EmailInput, db:AsyncSession=Depends(get_db)):
    return await forgot_password_service(data, db)

@router.post("/reset-password", status_code=200, response_model=APIResponse)
async def reset_password(data:ResetPassword, db:AsyncSession=Depends(get_db)):
    return await reset_password_service(data, db)

@router.post("/set-password", status_code=200, response_model=APIResponse)
async def set_password(data:SetPasswordInput, db:AsyncSession=Depends(get_db)):
    return await set_password_service(data, db)

