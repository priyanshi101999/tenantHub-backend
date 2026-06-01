from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends,HTTPException, status
from app.core.security import verify_token
from app.models.enums import Role
from app.models.user import User
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from sqlalchemy import select, func
from app.core.plan_features import PLAN_FEATURES
from app.models.task import Task

security= HTTPBearer()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication scheme")
    
    payload=verify_token(credentials.credentials)

    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized access")
    
    result= await db.execute(select(User).where(User.id==payload.get("user_id")))

    user=result.scalars().first()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    return user
    
def require_role(role:Role):
    async def checker(current_user:User=Depends(get_current_user)):
        if current_user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to perform this action")
        return current_user
    return checker


async def check_plan(action: str,db:AsyncSession=Depends(get_db),current_user:User=Depends(get_current_user)):
    plan=current_user.workspaces.plan

    if plan is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to perform this action")
    
    if action=="create_task":
        result=await db.execute(func.count(Task.id).select_from(Task).where(Task.workspace_id==current_user.workspace_id))

        task_count= result.scalars()

        if task_count > PLAN_FEATURES[plan]["max_tasks"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have reached the maximum number of tasks for this plan")
        
    if action=="create_user":
        result=await db.execute(func.count(User.id).select_from(User).where(User.workspace_id==current_user.workspace_id,User.role==Role.USER))

        user_count= result.scalars()

        if user_count > PLAN_FEATURES[plan]["max_users"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have reached the maximum number of users for this plan")
    
    return current_user
