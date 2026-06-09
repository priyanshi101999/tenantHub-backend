import asyncio
from datetime import datetime
from fastapi import HTTPException

from sqlalchemy import select
from fastapi import status
from app.api.deps import get_db
from app.core.celery import celery_app
from app.core.stripe_config import stripe
from app.db.session import AsyncSessionLocal
from app.models.enums import SubscriptionStatus
from app.models.event import StripeEvent
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.workspace import Workspace

@celery_app.task(bind=True, 
             max_retries=3, 
             autoretry_for=(Exception,), 
             retry_jitter=True, 
             retry_backoff=True, 
             retry_backoff_max=60)
def process_Stripe_event(self, event):
    asyncio.run(handle_event(event))

async def handle_event(event):
    
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(StripeEvent).where(StripeEvent.id == event["id"]))
            existing_event=result.scalars().first()

            if existing_event:
                return
            
            stripe_event = StripeEvent(id=event["id"], type=event["type"], processed=False)
            db.add(stripe_event)
            await db.commit()
            await db.refresh(stripe_event)

            data=event["data"]["object"]

            if event["type"] == "checkout.session.completed" and data.get("mode") == "subscription":
                stripe_subscription_id = data.get("subscription")
                workspace_id = int(data["metadata"]["workspace_id"])
                plan_id = int(data["metadata"]["plan_id"])

                stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                subscription_item_id = stripe_subscription["items"]["data"][0]["id"]

                subscription_query = await db.execute(select(Subscription).where(Subscription.workspace_id == workspace_id))
                subscription = subscription_query.scalars().first()

                if subscription is None:
                    subscription = Subscription(
                        workspace_id=workspace_id,
                        plan_id=plan_id,
                        stripe_subscription_id=stripe_subscription_id,
                        subscription_item_id=subscription_item_id,
                        status=SubscriptionStatus.INCOMPLETE,
                        cancel_at_period_end=False
                    )
                else:
                    subscription.plan_id = plan_id
                    subscription.stripe_subscription_id = stripe_subscription_id
                    subscription.subscription_item_id = subscription_item_id
                    if subscription.status != SubscriptionStatus.ACTIVE:
                        subscription.status = SubscriptionStatus.INCOMPLETE
                    subscription.cancel_at_period_end = False
                    subscription.pending_plan_id = None
                    subscription.pending_change_type = None

                db.add(subscription)

            if event["type"] == "invoice.paid":
                stripe_subscription_id = data["parent"]["subscription_details"]["subscription"]

                result = await db.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id == stripe_subscription_id
                    )
                )

                subscription = result.scalars().first()

                if not subscription:
                    stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
                    subscription_metadata = stripe_subscription.get("metadata") or {}
                    workspace_id = int(subscription_metadata["workspace_id"])
                    plan_id = int(subscription_metadata["plan_id"])

                    subscription = Subscription(
                        workspace_id=workspace_id,
                        plan_id=plan_id,
                        stripe_subscription_id=stripe_subscription_id,
                        subscription_item_id=stripe_subscription["items"]["data"][0]["id"],
                        status=SubscriptionStatus.INCOMPLETE,
                        cancel_at_period_end=False
                    )

                
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.current_period_end = datetime.fromtimestamp(
                    data["lines"]["data"][0]["period"]["end"]
                )

                if subscription.pending_change_type == "DOWNGRADE":
                    subscription.plan_id = subscription.pending_plan_id
                    subscription.pending_change_type = None
                    subscription.pending_plan_id = None

                workspace_query = await db.execute(select(Workspace).where(Workspace.id == subscription.workspace_id))
                workspace = workspace_query.scalars().first()

                if workspace is not None:
                    workspace.plan_id = subscription.plan_id
                    db.add(workspace)
                
                db.add(subscription)


            if event["type"] == "invoice.payment_failed":
                stripe_subscription_id = data["parent"]["subscription_details"]["subscription"]

                subscription_query = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id))
                subscription = subscription_query.scalars().first()

                if subscription is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

                subscription.status = SubscriptionStatus.PAST_DUE
                db.add(subscription)


            if event["type"] == "customer.subscription.updated":
                stripe_subscription_id = data["id"]

                subscription_query = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id))
                subscription = subscription_query.scalars().first()

                if subscription is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

                if data["status"] == "active":
                    subscription.status = SubscriptionStatus.ACTIVE
                subscription.current_period_end = datetime.fromtimestamp(data["items"]["data"][0]["current_period_end"])
                subscription.cancel_at_period_end = data.get("cancel_at_period_end", False)
                db.add(subscription)


            if event["type"] == "customer.subscription.deleted":
                stripe_subscription_id = data["id"]

                subscription_query = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id))
                subscription = subscription_query.scalars().first()

                if subscription is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

                free_plan_query = await db.execute(select(Plan).where(Plan.name == "FREE"))
                free_plan = free_plan_query.scalars().first()

                workspace_query = await db.execute(select(Workspace).where(Workspace.id == subscription.workspace_id))
                workspace = workspace_query.scalars().first()

                subscription.status = SubscriptionStatus.CANCELED
                subscription.cancel_at_period_end = False
                subscription.pending_plan_id = None
                subscription.pending_change_type = None

                if free_plan is not None:
                    subscription.plan_id = free_plan.id
                    if workspace is not None:
                        workspace.plan_id = free_plan.id
                        db.add(workspace)

                db.add(subscription)


            stripe_event.processed = True
            db.add(stripe_event)
            await db.commit()
            await db.refresh(stripe_event)

        except Exception as e:
            await db.rollback()
            raise
