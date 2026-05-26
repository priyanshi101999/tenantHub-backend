from app.core.database import engine
from sqlalchemy.orm import sessionmaker

SessionLocal=sessionmaker(bind=engine,autocommit=False, autoflush=False)

