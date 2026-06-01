from app.db.base import Base
from sqlalchemy import String, Enum, text, ForeignKey, func, DateTime
from .enums import Role
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class User(Base):
    __tablename__ ="users"

    id:             Mapped[int] = mapped_column(primary_key=True)
    name:           Mapped[str] = mapped_column(String(255))
    email:          Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password:       Mapped[str|None] = mapped_column()
    role:           Mapped[Role] = mapped_column(Enum(Role), default=Role.USER)
    email_verified: Mapped[bool] = mapped_column(default=False)
    workspace_id:   Mapped[int]  = mapped_column(ForeignKey("workspaces.id" , ondelete="CASCADE"), index=True)
    is_deleted:      Mapped[bool] = mapped_column(default=False)
    is_active:       Mapped[bool] = mapped_column(default=True)
    created_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True),default=func.now())
    updated_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True),default=func.now(), onupdate=func.now())

    workspace = relationship(
    "Workspace",
    back_populates="users",
    foreign_keys=[workspace_id],
    passive_deletes=True
)
    created_tasks = relationship(
    "Task",
    foreign_keys="Task.created_by",
    back_populates="created_by_user"
)

    assigned_tasks = relationship(
        "Task",
        foreign_keys="Task.assignee_id",
        back_populates="assignee"
    )