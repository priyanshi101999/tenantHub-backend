from app.core.config import settings
from sqlalchemy import create_engine

print(settings.database_url)
DATABASE_URL=settings.database_url
engine=create_engine(DATABASE_URL)



