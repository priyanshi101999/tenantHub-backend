from app.db.base import Base
from sqlalchemy import func, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime


class Workspace(Base):
    __tablename__="workspaces"

    id:          Mapped[int] = mapped_column(primary_key=True)
    name:        Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str|None] = mapped_column(Text, nullable=True)
    owner_id:    Mapped[int|None]  = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_deleted:    Mapped[bool] = mapped_column(default=False)
    is_active:    Mapped[bool] = mapped_column(default=True)
    plan_id:     Mapped[int|None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True),default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True),default=func.now(), onupdate=func.now())

    users = relationship(
    "User",
    back_populates="workspace",
    foreign_keys="User.workspace_id",
    passive_deletes=True

)
    tasks = relationship("Task", 
                         back_populates="workspace",
                           passive_deletes=True)


