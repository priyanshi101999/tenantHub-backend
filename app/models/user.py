from app.db.base import Base
from sqlalchemy import Integer, Column, String,DateTime, Enum, text, ForeignKey, Boolean
from .enums import Role
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ ="users"

    id=Column(Integer, nullable=False, primary_key=True, index=True)
    name=Column(String, nullable=False)
    email=Column(String, nullable=False, unique=True)
    password=Column(String,nullable=False)
    role=Column(Enum(Role), nullable=False, server_default=Role.USER.value)
    email_verified=Column(Boolean, server_default=text("false"), nullable=False)
    workspace_id=Column(Integer,ForeignKey("workspaces.id"),  nullable=False, index=True)
    created_at=Column(DateTime(timezone=True), nullable=False,server_default=text("now()") )
    updated_at=Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))
    workspace = relationship("Workspace", back_populates="users")
