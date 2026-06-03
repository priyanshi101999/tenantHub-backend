from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import SubscriptionStatus


class SubscriptionCancelOut(BaseModel):
    stripe_subscription_id: str
    cancel_at_period_end: bool
    status: SubscriptionStatus
    current_period_end: datetime

    model_config = ConfigDict(from_attributes=True)


    