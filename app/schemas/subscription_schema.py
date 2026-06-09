from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import SubscriptionStatus


class SubscriptionCancelOut(BaseModel):
    stripe_subscription_id: str
    cancel_at_period_end: bool
    status: SubscriptionStatus
    current_period_end: datetime

    model_config = ConfigDict(from_attributes=True)


class PlanOut(BaseModel):
    id: int
    name: str
    price: float
    stripe_price_id: str
    is_active: bool
    max_tasks: int
    max_users: int
    features: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

    
