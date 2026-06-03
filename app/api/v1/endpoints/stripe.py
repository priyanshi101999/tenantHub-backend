

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.api.deps import get_db
from app.schemas.user_schema import User
from app.schemas.response_schema import APIResponse
from app.services.stripe_service import confirm_payment_service, create_subscription_service, update_subscription_service, webhook_service, cancel_subscription_service


router= APIRouter(tags=["Stripe"])

@router.post("/subscription", status_code=201, response_model=APIResponse)
async def create_subscription(plan_id:int=Query(...), db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
     return await create_subscription_service(plan_id, db, current_user)
    
@router.post("/webhook", status_code=201)
async def webhook(request: Request, db:AsyncSession=Depends(get_db)):
    return await webhook_service(request, db)

@router.post("/subscription/cancel", status_code=201, response_model=APIResponse)
async def cancel_subscription(db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await cancel_subscription_service(db, current_user)

@router.post("/payment", status_code=201, response_model=APIResponse)
async def confirm_payment(db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await confirm_payment_service(db, current_user)

@router.post("/subscription/update", status_code=201, response_model=APIResponse)
async def update_subscription(plan_id:int=Query(...), db:AsyncSession=Depends(get_db), current_user:User=Depends(get_current_user)):
    return await update_subscription_service(plan_id,db, current_user)