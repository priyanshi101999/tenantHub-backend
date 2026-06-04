from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.core.stripe_config import stripe
from app.core.config import settings
from app.models.plan import Plan
from app.models.workspace import Workspace
from app.schemas.response_schema import APIResponse
from app.schemas.subscription_schema import SubscriptionCancelOut
from app.tasks.stripe_task import process_Stripe_event

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
        
        subscription_query=await db.execute(select(Subscription).where(Subscription.workspace_id == current_user.workspace_id))
        subscription=subscription_query.scalars().first()

        if subscription != None and not subscription.cancel_at_period_end:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail="An active subscription already exists. Please update your current subscription to change plans.")

        customer_id = await get_stripe_customer_id(workspace, admin_user, db)

        Stripe_subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": plan.stripe_price_id}],
            expand=["latest_invoice.confirmation_secret"],
            payment_behavior="default_incomplete"
        )

        print("Stripe_subscription.current_period_end",Stripe_subscription)

        if subscription is None:
            new_subscription = Subscription(
                stripe_subscription_id=Stripe_subscription.id,
                workspace_id=workspace.id,
                plan_id=plan.id,
                subscription_item_id=Stripe_subscription.items.data[0].id,
                status=SubscriptionStatus.INCOMPLETE,
                cancel_at_period_end=False
            )

            db.add(new_subscription)
        else:
            subscription.plan_id=plan.id
            subscription.subscription_item_id=Stripe_subscription.items.data[0].id
            subscription.status=SubscriptionStatus.INCOMPLETE
            subscription.cancel_at_period_end=False
            workspace_id=workspace.id

            db.add(subscription)

        await db.commit()
        
        return APIResponse(
            status=200,
            message="Subscription created successfully",
            data={"subscription_id": Stripe_subscription.id, "client_secret": Stripe_subscription.latest_invoice.confirmation_secret.client_secret}
        )
    
    except HTTPException:
        await db.rollback()
        raise
        
    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create subscription")

  
async def webhook_service(request, db):
    signature = request.headers.get("Stripe-Signature")
    payload = await request.body()

    event = stripe.Webhook.construct_event(
        payload,
        signature,
        settings.stripe_webhook_secret
    ) 

    event = event.to_dict()
    print("webhook_service.event",event)
    process_Stripe_event.delay(event)

    return {"ok":True}


async def cancel_subscription_service(db, current_user):
    try:
        workspace_query = await db.execute(select(Workspace).where(Workspace.id == current_user.workspace_id))
        workspace = workspace_query.scalars().first()

        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, details="Workspace not found")
   
        result = await db.execute(select(Subscription).where(Subscription.workspace_id == workspace.id))
        subscription = result.scalars().first()

        if subscription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, details="Subscription not found")
        
        if subscription.cancel_at_period_end:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, details="Subscription already cancelled")
        
        stripe.Subscription.modify(subscription.stripe_subscription_id, cancel_at_period_end=True)

        subscription.cancel_at_period_end = True
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

        return APIResponse(
            status=200,
            message="Subscription cancelled successfully",
            data=SubscriptionCancelOut.model_validate(subscription)
        )
    
    except HTTPException:
        await db.rollback()
        raise
    
    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cancel subscription")
        
async def update_subscription_service(plan_id,db, current_user):

    try:
        result = await db.execute(select(Workspace).where(Workspace.id == current_user.workspace_id))
        workspace = result.scalars().first()

        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, details="Workspace not found")
        
        plan_query = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_query.scalars().first()

        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, details="Plan not found")
        
        subscription_query = await db.execute(select(Subscription).where(Subscription.workspace_id == workspace.id))
        subscription = subscription_query.scalars().first()

        if subscription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        
        current_plan_query=await db.execute(select(Plan).where(Plan.id == subscription.plan_id))
        current_plan=current_plan_query.scalars().first()

        if subscription.plan_id == plan_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already subscribed to this plan")

        if plan.price > current_plan.price:
            stripe_subscription = stripe.Subscription.modify(subscription.stripe_subscription_id,
                                                            items=[{"id": subscription.subscription_item_id, "price": plan.stripe_price_id}],
                                                            proration_behavior="create_prorations"
                                                            )
            subscription.plan_id=plan_id
            subscription.pending_plan_id=None
            subscription.pending_change_type=None

            message = "Subscription upgraded successfully"
            
        else:
            stripe_subscription = stripe.Subscription.modify(subscription.stripe_subscription_id,
                                                            items=[{"id": subscription.subscription_item_id, "price": plan.stripe_price_id}],
                                                            proration_behavior="none"
                                                            )
            subscription.pending_plan_id=plan_id
            subscription.pending_change_type="DOWNGRADE"
            message = "Downgrade scheduled for next billing cycle"

        db.add(subscription)
        await db.commit()
            
        return APIResponse(
            status=200,
            message=message
        )
    
    except HTTPException:
        await db.rollback()
        raise
    
    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update subscription")


async def confirm_payment_service(payment_intent_id,db, current_user):
    try:

        response = stripe.PaymentIntent.confirm(payment_intent_id,payment_method="pm_card_visa")

        print("response",response)
       
        if response.status != "succeeded":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to confirm payment")
        
        return APIResponse(
            status=200,
            message="Payment confirmed successfully"
        )
    
    except HTTPException:
        await db.rollback()
        raise
    
    except Exception as e:
        await db.rollback()
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to confirm payment")