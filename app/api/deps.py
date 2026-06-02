from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends,HTTPException, status
from app.core.security import verify_token
from app.models.enums import Role
from app.models.plan import Plan
from app.models.user import User
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

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
    
    result= await db.execute(select(User).options(selectinload(User.workspace)).where(User.id==payload.get("user_id")))

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

def check_plan(plan):
    async def checker(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
        result=await db.execute(select(Plan).where(Plan.id==current_user.workspace.plan_id))
        current_plan=result.scalars().first()

        if current_plan.name not in plan:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can not perform this action with your current plan")
        
        return current_user
    
    return checker



