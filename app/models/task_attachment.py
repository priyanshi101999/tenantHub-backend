from app.db.base import Base
from sqlalchemy import func, text, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

class TaskAttachment(Base):

    __tablename__="task_attachments"

    id:         Mapped[int] = mapped_column(primary_key=True)
    task_id:    Mapped[int] = mapped_column(ForeignKey("tasks.id" , ondelete="CASCADE"), index=True)
    uploaded_by:Mapped[int| None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    file_name:  Mapped[str] = mapped_column(String(255))
    file_size:  Mapped[int] = mapped_column()
    file_path:  Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    task=relationship(
        "Task",
        back_populates="attachments",
        passive_deletes=True,
        foreign_keys=[task_id]
    )
