from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.core.stripe_config import stripe
from app.core.config import settings
from app.models.plan import Plan
from app.models.workspace import Workspace
from app.schemas.response_schema import APIResponse

async def get_stripe_customer_id(workspace,user, db):
    try:
        if workspace.stripe_customer_id:
            return workspace.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            metadata={"workspace_id": workspace.id}
        )

        workspace.stripe_customer_id = customer.id
        db.add(workspace)
        await db.commit()

        return customer.id
    
    except stripe.error.StripeError as e:
        await db.rollback()
        print("Stripe error:", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error communicating with Stripe")

async def create_subscription_service(plan_id, db, current_user):

    try:
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalars().first()

        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        
        workspace_query = await db.execute(select(Workspace).where(Workspace.id == current_user.workspace_id))
        workspace = workspace_query.scalars().first()

        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, details="Workspace not found")

        user_query=await db.execute(select(User).where(User.workspace_id==workspace.id, User.role=="ADMIN"))
        admin_user=user_query.scalars().first()

        if admin_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, details="Admin user not found")

        customer_id = await get_stripe_customer_id(workspace, admin_user, db)

        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": plan.stripe_price_id}],
            expand=["latest_invoice.payment_intent"],
            payment_behavior="default_incomplete"
        )

        return APIResponse(
            status=200,
            message="Subscription created successfully",
            data={"subscription_id": subscription.id, "client_secret": subscription.latest_invoice.payment_intent.client_secret}
        )
    
    except HTTPException:
        await db.rollback()
        raise
        
    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create subscription")
    
async def webhook_service(request, db, current_user):
    signature = request.headers.get("Stripe-Signature")
    payload = await request.body()

    event = stripe.Webhook.construct_event(
        payload,
        signature,
        settings.stripe_webhook_secret
    ) 

    return {"ok":True}



        
        
 