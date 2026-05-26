from app.db.base import Base
from sqlalchemy import Column,Integer, String, Boolean, DateTime, text, ForeignKey

class RefreshToken(Base):
    __tablename__="refresh_tokens"

    id=Column(Integer, nullable=False, primary_key=True)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False, index=True)
    token=Column(String, nullable=False)
    expired_at=Column(DateTime(timezone=True), nullable=False)
    is_invoked=Column(Boolean, nullable=False, server_default=text("false"))
    created_at=Column(DateTime(timezone=True), nullable=False, server_default=text("now()") )
    updated_at=Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))
