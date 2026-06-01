from app.db.base import Base
from sqlalchemy import func, String,ForeignKey, Enum, Text
from .enums import TaskStatus, Priority
from sqlalchemy.orm import mapped_column, Mapped, relationship
from datetime import datetime

class Task(Base):
    __tablename__ = "tasks"

    id:           Mapped[int] =mapped_column(primary_key=True)
    workspace_id: Mapped[int] =mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    title:        Mapped[str] = mapped_column(String(255))
    description:  Mapped[str|None] = mapped_column(Text, nullable=True)
    status:       Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.TODO)
    created_by:   Mapped[int|None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assignee_id:  Mapped[int|None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date:     Mapped[datetime|None] = mapped_column(nullable=True)
    priority:     Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.MEDIUM)
    created_at:   Mapped[datetime] = mapped_column(default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    workspace = relationship("Workspace", back_populates="tasks", foreign_keys=[workspace_id], passive_deletes=True)
    created_by_user = relationship(
    "User",
    foreign_keys=[created_by],
    back_populates="created_tasks",
)
    assignee = relationship(
    "User",
    foreign_keys=[assignee_id],
    back_populates="assigned_tasks"
)
    attachments=relationship(
        "TaskAttachment",
        back_populates="task",
        passive_deletes=True,
        cascade="all, delete-orphan"
    )








   

