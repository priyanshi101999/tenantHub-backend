from app.db.base import Base
from sqlalchemy import Column, Integer, String, DateTime, text
class OTP(Base):
    __tablename__="otp"

    id=Column(Integer,primary_key=True, nullable=False)
    email=Column(String, nullable=False, index=True)
    expire_at=Column(DateTime(timezone=True), nullable=False)
    code=Column(String,nullable=False)
    created_at=Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

