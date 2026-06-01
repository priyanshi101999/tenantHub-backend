from app.models.enums import Role
from app.models.user import User
from fastapi import HTTPException, status
from app.schemas.response_schema import APIResponse
from app.schemas.user_schema import UserOut, InviteUserOut
from app.core.redis_client import redis_client as redis
from app.utils.secret_key import generate_invite_token
from app.core.config import settings
from app.tasks.email_task import send_email_task
from app.templates.invite_mail import get_invite_email_template
from fastapi import status, HTTPException
from sqlalchemy import select


async def add_user_service(data, db):
    data = data.model_dump()

    try:
        result = await db.execute(select(User).where(User.email == data["email"]))
        existing_user=result.scalars().first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )

        user = User(**data)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return APIResponse(
            status=status.HTTP_201_CREATED,
            message="User added successfully",
            data={"user": UserOut.model_validate(user)}
        )

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        print("Error:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add user"
        )
    
    
async def invite_user_service(data, db):
    email=data.email

    result=await db.execute(select(User).where(User.email==data.email))
    existing_user=result.scalars().first()

    if existing_user==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    

    secret_token=generate_invite_token()

    await redis.set(f"invite_token:{secret_token}", email, ex=86400)

    invite_link=f"{settings.frontend_baseurl}/invite/{secret_token}"


    html_template=get_invite_email_template(invite_link, "24 hours")

    send_email_task.delay(email, "Invite User", html_template)

    output_data={
        "email": email,
        "invite_link": invite_link
    }

    return APIResponse(
        message="Invite sent successfully",
        data=InviteUserOut.model_validate(output_data),
        status=status.HTTP_200_OK
    )

async def user_list_service(db, current_user):
    
    workspace_id=current_user.workspace_id

    if current_user.role !=Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You not have access")
    
    result=await db.execute(select(User).where(User.workspace_id==workspace_id, User.isDeleted==False,User.role==Role.USER))
    user_list=result.scalars().all()
    data=[UserOut.model_validate(u) for u in user_list]

    return APIResponse(
        message="User List fetched successfully",
        data=data,
        status=200
    )
        
async def delete_user_service(id, db, current_user):

    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to perform this action")
    
    user_id=id

    result=await db.execute(select(User).where(User.id==user_id, User.isDeleted==False))
    existing_user=result.scalars().first()

    if existing_user==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if existing_user.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You can not delete user from other workspace")
    
    try:
        existing_user.isDeleted=True
        db.add(existing_user)
        await db.commit()
        return APIResponse(
            message="User deleted successfully",
            status=200
        )
    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=500, detail="Failed to delete user")

    




 
 