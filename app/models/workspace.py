from app.db.base import Base
from sqlalchemy import Integer, Column, String,DateTime, Boolean, text
from sqlalchemy.orm import relationship



class Workspace(Base):
    __tablename__="workspaces"

    id=Column(Integer, nullable=False, primary_key=True, index=True)
    name=Column(String, nullable=False)
    description=Column(String,nullable=True)
    owner_id=Column(Integer, nullable=True)
    isdelete=Column(Boolean, nullable=False, server_default=text("false"))
    isActive=Column(Boolean, nullable=True, server_default=text("true"))
    created_at=Column(DateTime(timezone=True), nullable=False,server_default=text("now()") )
    updated_at=Column(DateTime(timezone=True), nullable=False,server_default=text("now()"), onupdate=text("now()"))
    users = relationship("User", back_populates="workspace")
