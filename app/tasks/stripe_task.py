import asyncio
from datetime import datetime
from fastapi import HTTPException

from sqlalchemy import select
from fastapi import status
from app.api.deps import get_db
from app.core.celery import celery
from app.db.session import AsyncSessionLocal
from app.models.enums import SubscriptionStatus
from app.models.event import StripeEvent
from app.models.subscription import Subscription

@celery.task(bind=True, 
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

            print("event_print",event)
            if event["type"] == "invoice.paid":
                stripe_subscription_id = data["parent"]["subscription_details"]["subscription"]

                result = await db.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id == stripe_subscription_id
                    )
                )

                subscription = result.scalars().first()

                if not subscription:
                    raise HTTPException(status_code=404, detail="Subscription not found")

                
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.current_period_end = datetime.fromtimestamp(
                    data["lines"]["data"][0]["period"]["end"]
                )
                db.add(subscription)
                await db.flush()
                await db.commit()

            if event["type"] == "invoice.payment_failed":
                stripe_subscription_id = data["parent"]["subscription_details"]["subscription"]

                subscription_query = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id))
                subscription = subscription_query.scalars().first()

                if subscription is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

                subscription.status = "PAST_DUE"
                db.add(subscription)
                await db.commit()

            if event["type"] == "customer.subscription.updated":
                stripe_subscription_id = data["id"]

                subscription_query = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id))
                subscription = subscription_query.scalars().first()

                if subscription is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

                subscription.status = SubscriptionStatus.ACTIVE
                subscription.current_period_end = datetime.fromtimestamp(data["items"]["data"][0]["current_period_end"])
                db.add(subscription)
                await db.commit()

            if event["type"] == "customer.subscription.deleted":
                stripe_subscription_id = data["id"]

                subscription_query = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id))
                subscription = subscription_query.scalars().first()

                if subscription is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

                subscription.status = "CANCELED"
                db.add(subscription)
                await db.commit()

            stripe_event.processed = True
            db.add(stripe_event)
            await db.commit()
            await db.refresh(stripe_event)

        except Exception as e:
            print("Error processing Stripe event:", e)
            await db.rollback()
            raise
