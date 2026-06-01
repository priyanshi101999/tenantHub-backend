from app.core.database import engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

AsyncSessionLocal=sessionmaker(bind=engine,
                               class_=AsyncSession,
                               expire_on_commit=False
                               )

