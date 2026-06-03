

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.api.deps import get_db
from app.schemas.user_schema import User
from app.schemas.response_schema import APIResponse
from app.services.stripe_service import create_subscription_service, webhook_service


router= APIRouter(tags=["Stripe"])

@router.post("/subscription", status_code=201, response_model=APIResponse)
async def create_subscription(plan_id:int=Query(...), db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
     return await create_subscription_service(plan_id, db, current_user)
    
@router.post("/webhook", status_code=201)
async def webhook(request: Request, db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await webhook_service(request, db, current_user)