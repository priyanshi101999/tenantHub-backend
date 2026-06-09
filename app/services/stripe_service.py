from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.core.stripe_config import stripe
from app.core.config import settings
from app.core.plan_features import PLAN_FEATURES
from app.models.plan import Plan
from app.models.workspace import Workspace
from app.schemas.response_schema import APIResponse
from app.schemas.subscription_schema import PlanOut, SubscriptionCancelOut
from app.core.task_dispatcher import dispatch_stripe_event


def stripe_value(obj, key, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    try:
        return obj.get(key, default)
    except AttributeError:
        return getattr(obj, key, default)

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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create subscription")


async def create_checkout_session_service(plan_id, db, current_user):
    try:
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalars().first()

        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        workspace_query = await db.execute(select(Workspace).where(Workspace.id == current_user.workspace_id))
        workspace = workspace_query.scalars().first()

        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        user_query = await db.execute(select(User).where(User.workspace_id == workspace.id, User.role == "ADMIN"))
        admin_user = user_query.scalars().first()

        if admin_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

        subscription_query = await db.execute(select(Subscription).where(Subscription.workspace_id == workspace.id))
        subscription = subscription_query.scalars().first()

        if subscription is not None and not subscription.cancel_at_period_end and subscription.status != SubscriptionStatus.CANCELED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An active subscription already exists. Please update your current subscription to change plans."
            )

        customer_id = await get_stripe_customer_id(workspace, admin_user, db)
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.frontend_baseurl}/billing?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_baseurl}/billing?checkout=cancelled",
            client_reference_id=str(workspace.id),
            metadata={
                "workspace_id": str(workspace.id),
                "plan_id": str(plan.id)
            },
            subscription_data={
                "metadata": {
                    "workspace_id": str(workspace.id),
                    "plan_id": str(plan.id)
                }
            }
        )

        return APIResponse(
            status=200,
            message="Checkout session created successfully",
            data={
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id
            }
        )

    except HTTPException:
        raise

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error communicating with Stripe")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create checkout session")


async def complete_checkout_session_service(session_id, db, current_user):
    try:
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["subscription"]
        )

        if stripe_value(checkout_session, "mode") != "subscription" or stripe_value(checkout_session, "status") != "complete":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Checkout session is not complete")

        if stripe_value(checkout_session, "payment_status") not in ("paid", "no_payment_required"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Checkout payment is not complete")

        stripe_subscription = stripe_value(checkout_session, "subscription")
        if isinstance(stripe_subscription, str):
            stripe_subscription = stripe.Subscription.retrieve(stripe_subscription)

        session_metadata = stripe_value(checkout_session, "metadata", {}) or {}
        subscription_metadata = stripe_value(stripe_subscription, "metadata", {}) or {}
        workspace_id = int(
            stripe_value(session_metadata, "workspace_id")
            or stripe_value(subscription_metadata, "workspace_id")
            or stripe_value(checkout_session, "client_reference_id")
        )

        if workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Checkout session does not belong to your workspace")

        subscription_items = stripe_value(stripe_value(stripe_subscription, "items", {}), "data", [])
        if not subscription_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe subscription has no items")

        subscription_item = subscription_items[0]
        stripe_price_id = stripe_value(stripe_value(subscription_item, "price", {}), "id")
        plan_id = stripe_value(session_metadata, "plan_id") or stripe_value(subscription_metadata, "plan_id")

        if plan_id is not None:
            plan_id = int(plan_id)
        else:
            plan_query = await db.execute(select(Plan).where(Plan.stripe_price_id == stripe_price_id))
            plan = plan_query.scalars().first()

            if plan is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found for Stripe price")

            plan_id = plan.id

        current_period_end = stripe_value(subscription_item, "current_period_end") or stripe_value(stripe_subscription, "current_period_end")

        workspace_query = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        workspace = workspace_query.scalars().first()

        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        subscription_query = await db.execute(select(Subscription).where(Subscription.workspace_id == workspace_id))
        subscription = subscription_query.scalars().first()

        if subscription is None:
            subscription = Subscription(
                stripe_subscription_id=stripe_value(stripe_subscription, "id"),
                workspace_id=workspace_id,
                plan_id=plan_id,
                subscription_item_id=stripe_value(subscription_item, "id"),
                status=SubscriptionStatus.ACTIVE,
                cancel_at_period_end=False
            )
        else:
            subscription.stripe_subscription_id = stripe_value(stripe_subscription, "id")
            subscription.workspace_id = workspace_id
            subscription.plan_id = plan_id
            subscription.subscription_item_id = stripe_value(subscription_item, "id")
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.cancel_at_period_end = False
            subscription.pending_plan_id = None
            subscription.pending_change_type = None

        if current_period_end:
            subscription.current_period_end = datetime.fromtimestamp(current_period_end)

        workspace.plan_id = plan_id
        db.add(workspace)
        db.add(subscription)
        await db.commit()

        return APIResponse(
            status=200,
            message="Subscription activated successfully",
            data={
                "subscription_id": subscription.stripe_subscription_id,
                "plan_id": plan_id
            }
        )

    except HTTPException:
        await db.rollback()
        raise

    except stripe.error.StripeError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error communicating with Stripe")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete checkout session")


async def get_subscription_plans_service(db, current_user):
    try:
        result = await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.price.asc()))
        plans = result.scalars().all()
        subscription_result = await db.execute(
            select(Subscription).where(Subscription.workspace_id == current_user.workspace_id)
        )
        subscription = subscription_result.scalars().first()
        has_active_subscription = subscription is not None and not subscription.cancel_at_period_end and subscription.status != SubscriptionStatus.CANCELED
        current_plan_id = subscription.plan_id if has_active_subscription else current_user.workspace.plan_id
        current_plan_name = None

        data = []
        for plan in plans:
            if plan.id == current_plan_id:
                current_plan_name = plan.name

            features = PLAN_FEATURES.get(plan.name.upper(), {})
            data.append(PlanOut(
                id=plan.id,
                name=plan.name,
                price=plan.price,
                stripe_price_id=plan.stripe_price_id,
                is_active=plan.is_active,
                max_tasks=plan.max_tasks,
                max_users=plan.max_users,
                features=features
            ))

        return APIResponse(
            status=200,
            message="Subscription plans retrieved successfully",
            data={
                "plans": data,
                "current_plan_id": current_plan_id,
                "current_plan_name": current_plan_name,
                "has_active_subscription": has_active_subscription,
                "subscription": {
                    "id": subscription.id,
                    "plan_id": subscription.plan_id,
                    "status": subscription.status,
                    "cancel_at_period_end": subscription.cancel_at_period_end,
                    "current_period_end": subscription.current_period_end
                } if subscription else None
            }
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve subscription plans")

  
async def webhook_service(request, db):
    signature = request.headers.get("Stripe-Signature")
    payload = await request.body()

    event = stripe.Webhook.construct_event(
        payload,
        signature,
        settings.stripe_webhook_secret
    ) 

    event = event.to_dict()
    dispatch_stripe_event(event)

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

        free_plan_query = await db.execute(select(Plan).where(Plan.name == "FREE"))
        free_plan = free_plan_query.scalars().first()
        
        stripe.Subscription.modify(subscription.stripe_subscription_id, cancel_at_period_end=True)

        subscription.cancel_at_period_end = True
        if free_plan is not None:
            subscription.pending_plan_id = free_plan.id
            subscription.pending_change_type = "CANCEL_TO_FREE"
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
            workspace.plan_id=plan_id
            db.add(workspace)

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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update subscription")


async def confirm_payment_service(payment_intent_id,db, current_user):
    try:

        response = stripe.PaymentIntent.confirm(payment_intent_id,payment_method="pm_card_visa")

       
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to confirm payment")
