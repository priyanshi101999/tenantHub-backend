from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

print(settings.database_url)
DATABASE_URL=settings.database_url
engine=create_async_engine(DATABASE_URL, echo=True)





