from datetime import datetime
from sqlalchemy import String, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class StripeEvent(Base):
    __tablename__="stripe_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[str] = mapped_column(String(255))
    processed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=func.now())
