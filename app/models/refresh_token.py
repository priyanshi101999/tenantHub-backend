from app.db.base import Base
from sqlalchemy import func, text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class RefreshToken(Base):
    __tablename__="refresh_tokens"

    id:         Mapped[int] = mapped_column(primary_key=True)
    user_id:    Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),index=True)
    token:      Mapped[str] = mapped_column()
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_invoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
