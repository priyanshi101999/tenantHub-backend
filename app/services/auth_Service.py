from app.models.workspace import Workspace
from app.models.user import User
from app.schemas.user_schema import UserOut
from app.models.refresh_token import RefreshToken
from app.core.security import hash_password, verify_password, create_jwt_token, create_refresh_token
from app.templates.otp_email import otp_email_template
from app.tasks.email_task import send_email_task
from app.utils.secret_key import generate_otp
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.schemas.auth_schema import OTPInput,LoginOut
from fastapi import HTTPException, status
from app.core.redis_client import redis_client as redis
from app.schemas.response_schema import APIResponse
from sqlalchemy import select,delete
from sqlalchemy.orm import selectinload


async def register_user_service(registerData, db):
    print(registerData)
    try:
        result=await db.execute(select(User).options(selectinload(User.workspace)).where(User.email==registerData.email))
        existing_email=result.scalars().first()

        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

        workSpaceData={
            "name": registerData.workspaceName,
            "owner_id" : None
        }

        workspace=Workspace(**workSpaceData)
        db.add(workspace)
        await db.flush()

        hashed_password=hash_password(registerData.password)
        
        userData={
            "name": registerData.name,
            "email": registerData.email,
            "password": hashed_password,
            "workspace_id": workspace.id,
            "email_verified": False,
            "role": registerData.role
        }

        user=User(**userData)
        db.add(user)
        await db.flush()

        workspace.owner_id=user.id
        await db.commit()
        await db.refresh(user)
        print("user", user)

        return APIResponse(
            message="Registered successfully",
            data=UserOut.model_validate(user),
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to register user")



async def verify_email_service(email, db):
    
    otp=generate_otp()
    print("otp", otp)
    html_content=otp_email_template(otp)

    try:
        send_email_task.delay(email, "Email Verification", html_content)
        await redis.set(f"email_verification:{email}", otp, ex=300)
        return APIResponse(message="Email sent successfully", status=status.HTTP_200_OK)
    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Email sending failed")
    
async def verify_otp_service(OtpData: OTPInput,db):

    existing_otp=await redis.get(f"email_verification:{OtpData.email}")
    print("existing_otp", existing_otp, OtpData.code)

    if existing_otp == None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")
    
    if str(existing_otp) == str(OtpData.code):
        print("existing_otp.matched")
        try:
            result=await db.execute(select(User).where(User.email==OtpData.email))
            user=result.scalars().first()
            
            if user==None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            
            print("user", user)
            
            user.email_verified=True
            db.add(user)
            await db.commit()
            await redis.delete(f"email_verification:{OtpData.email}")
            return APIResponse(message="Email verified successfully", 
                               status=status.HTTP_200_OK)
        
        except HTTPException:
            await db.rollback()
            raise

        except Exception as e:
            print(e)
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify email")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")


async def login_service(loginData,db):
    email=loginData.email
    password=loginData.password

    result=await db.execute(select(User).where(User.email==email))
    existing_user=result.scalars().first()

    if existing_user == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if existing_user.email_verified == False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not verified")
    
    if verify_password(password, existing_user.password) == False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    
    access_token=create_jwt_token({"user_id": existing_user.id, "workspace_id": existing_user.workspace_id})
    refresh_token=create_refresh_token({"user_id": existing_user.id, "workspace_id": existing_user.workspace_id})

    refresh_Token_data={
        "user_id":existing_user.id,
        "token":refresh_token,
        "expired_at":datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_expire_days)
    }

    try:
        db.add(RefreshToken(**refresh_Token_data))
        await db.commit()
    except Exception as e:
        print(e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to login")

    login_data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer"
    }

    return APIResponse(message="Login successful", 
                       data= LoginOut.model_validate(login_data), status=status.HTTP_200_OK)

async def refresh_token_service(data:dict, db):
    refresh_token=data.refresh_token

    result=await db.execute(select(RefreshToken).where(RefreshToken.token==refresh_token, RefreshToken.is_invoked==False))
    existing_token=result.scalars().first()

    if existing_token == None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") 
    
    if datetime.now(timezone.utc) > existing_token.expired_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired refresh token") 
    
    access_token=create_jwt_token({"user_id":existing_token.user_id, "workspace_id":existing_token.workspace_id})

    return APIResponse(message="Token refreshed successfully", 
                       data={"access_token": access_token, "token_type": "Bearer"},
                         status=status.HTTP_200_OK)
    

async def change_password_service(data, db, current_user):
    old_password=data.old_password
    new_password=data.new_password

    if verify_password(old_password, current_user.password) == False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect old password")
    
    current_user.password=hash_password(new_password)
    db.add(current_user)
    await db.commit()

    return APIResponse(message="Password changed successfully", 
                       status=status.HTTP_200_OK)

async def forgot_password_service(email, db):
    otp=generate_otp()

    html_content=otp_email_template(otp)
    try:
        result=await db.execute(select(User).where(User.email==email))
        existing_user=result.scalars().first()

        if existing_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
        send_email_task.delay(email, "Forgot Password", html_content)
        await redis.set(f"forgot_password:{email}", otp, ex=300)
        return APIResponse(message="OTP sent successfully", status=status.HTTP_200_OK)
    
    except HTTPException:
        raise

    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send OTP")

async def reset_password_service(data,db):
    otp=data.otp
    new_password=data.new_password
    email=data.email

    stored_otp=await redis.get(f"forgot_password:{email}")

    if str(stored_otp) != str(otp):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")
    
    result=await db.execute(select(User).where(User.email==email))
    existing_user=result.scalars().first()

    if existing_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    try:
        existing_user.password=hash_password(new_password)
        await db.commit()
        await redis.delete(f"forgot_password:{email}")
    except Exception as e:
        print("Error", e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset password")
    
    return APIResponse(message="Password reset successfully", status=status.HTTP_200_OK)

async def set_password_service(data, db):
    password=data.password
    secret_token=data.secret_token

    email=await redis.get(f"invite_token:{secret_token}")

    if email is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    
    result=await db.execute(select(User).where(User.email==email))
    user=result.scalars().first()


    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    access_token=create_jwt_token({"user_id": user.id, "workspace_id": user.workspace_id})
    refresh_token=create_refresh_token({"user_id": user.id, "workspace_id": user.workspace_id})
    refresh_Token_data={
        "user_id":user.id,
        "token":refresh_token,
        "expired_at":datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_expire_days)
    }

    try:
        print("row.password", password)
        await db.execute(delete(RefreshToken).where(RefreshToken.user_id==user.id))
        user.password=hash_password(password)
        print("user.password", user.password)
        user.email_verified=True
        db.add(RefreshToken(**refresh_Token_data))
        db.add(user)
        await db.commit()
        await redis.delete(f"invite_token:{secret_token}")
    except Exception as e:
        print("Error", e)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set password")

    login_data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer"
    }

    return APIResponse(message="set password successful", 
                       data= LoginOut.model_validate(login_data), status=status.HTTP_200_OK)



   







    

