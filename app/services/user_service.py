from app.models.enums import Role
from app.models.plan import Plan
from app.models.user import User
from fastapi import HTTPException, status
from app.schemas.response_schema import APIResponse
from app.schemas.user_schema import UserOut, InviteUserOut
from app.core.redis_client import redis_client as redis
from app.utils.secret_key import generate_invite_token
from app.core.config import settings
from app.core.task_dispatcher import dispatch_email
from app.templates.invite_mail import get_invite_email_template
from fastapi import status, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import math


async def add_user_service(data, db, current_user):
    data = data.model_dump()
    print("data", data)
    print("current_user", current_user.workspace_id)

    try:
        requested_workspace_id = data.pop("workspace_id", None)
        if requested_workspace_id is not None and requested_workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only add users to your own workspace")

        result = await db.execute(select(User).options(selectinload(User.workspace)).where(User.email == data["email"]))
        existing_user=result.scalars().first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )

        existing_phone_query = await db.execute(select(User).where(User.phone == data["phone"]))
        existing_phone = existing_phone_query.scalars().first()

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists"
            )

        plan_query = await db.execute(select(Plan).where(Plan.id == current_user.workspace.plan_id))
        current_plan = plan_query.scalars().first()

        if current_plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        user_count_query = await db.execute(
            select(func.count(User.id)).where(
                User.workspace_id == current_user.workspace_id,
                User.is_deleted == False,
                User.role == Role.USER
            )
        )
        user_count = user_count_query.scalar()

        if user_count >= current_plan.max_users:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have reached the maximum number of users for this plan")

        user = User(**data, workspace=current_user.workspace)
        db.add(user)
        await db.commit()
        await db.refresh(user, attribute_names=["workspace"])

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

    dispatch_email(email, "Invite User", html_template)

    output_data={
        "email": email,
        "invite_link": invite_link
    }

    return APIResponse(
        message="Invite sent successfully",
        data=InviteUserOut.model_validate(output_data),
        status=status.HTTP_200_OK
    )

async def user_list_service(page: int, size: int, db, current_user: User):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You not have access")
    
    workspace_id=current_user.workspace_id

    result=await db.execute(select(User).options(selectinload(User.workspace)).where(User.workspace_id==workspace_id, User.is_deleted==False,User.role==Role.USER).limit(size).offset((page-1)*size))
    user_list=result.scalars().all()
    count_result=await db.execute(select(func.count(User.id)).where(User.workspace_id==workspace_id, User.is_deleted==False,User.role==Role.USER))
    total_items=count_result.scalar()
    data=[UserOut.model_validate(u) for u in user_list]

    return APIResponse(
        message="User List fetched successfully",
            data={
                "users": data,
                "pagination": {
                "page": page,
                "size": size,
                "total_pages": math.ceil(total_items/size),
                "total_items": total_items
                }
        },
        status=200
    )
        
async def delete_user_service(id, db, current_user):

    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to perform this action")
    
    user_id=id

    result=await db.execute(select(User).where(User.id==user_id, User.is_deleted==False))
    existing_user=result.scalars().first()

    if existing_user==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if existing_user.workspace_id != current_user.workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You can not delete user from other workspace")
    
    try:
        existing_user.is_deleted=True
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


async def get_user_service(id,db,current_user):

    try:

        result=await db.execute(select(User).options(selectinload(User.workspace)).where(User.id==id, User.is_deleted==False))
        existing_user=result.scalars().first()

        if existing_user==None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        if existing_user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You can not get user from other workspace")
        
        return APIResponse(
            message="User fetched successfully",
            data=UserOut.model_validate(existing_user),
            status=status.HTTP_200_OK
        )
    
    except HTTPException:
        await db.rollback()
        raise
    
    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=500, detail="Failed to get user")
    






 
 
