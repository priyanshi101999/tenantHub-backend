from http.client import HTTPException

from sqlalchemy import select
from starlette import status

from app.core import celery
from app.models.event import StripeEvent


@celery.task(bind=True,max_retries=3)
async def precess_Stripe_event(self,event, db):
    try:

        result = await db.execute(select(StripeEvent).where(StripeEvent.id == event.id))
        existing_event=result.scalars().first()

        if existing_event:
            return
        
        stripe_event = StripeEvent(id=event.id, type=event.type, processed=False)
        db.add(stripe_event)
        await db.commit()
        await db.refresh(stripe_event)

    except Exception as e:
        print("Error processing Stripe event:", e)
        await db.rollback()
        self.retry(exc=e, countdown=10)