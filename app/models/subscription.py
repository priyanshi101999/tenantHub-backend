from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime
from sqlalchemy import Enum, ForeignKey, func, String, DateTime
from app.models.enums import SubscriptionStatus

class Subscription(Base):
    __tablename__ = "subscriptions"

    id:                     Mapped[int] = mapped_column(primary_key=True)
    workspace_id:           Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    plan_id:                Mapped[int] = mapped_column(ForeignKey("plans.id"))
    stripe_subscription_id: Mapped[str] = mapped_column(String(255))
    subscription_item_id:   Mapped[str] = mapped_column(String(255))
    current_period_end:     Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end:   Mapped[bool] = mapped_column(default=False)
    status:                 Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus),default=SubscriptionStatus.INCOMPLETE)
    created_at:             Mapped[datetime] = mapped_column(DateTime(timezone=True),default=func.now())
    updated_at:             Mapped[datetime] = mapped_column(DateTime(timezone=True),default=func.now(), onupdate=func.now())