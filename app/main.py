from fastapi import FastAPI
from fastapi import Depends
from app.api.v1.router import router
from app.api.deps import get_db
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        settings.frontend_url
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True

)


@app.get("/")
def greeting():
    return {"message": "TenantHub API is running"}

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    await db.execute(text("select 1"))
    return {"status": "ok", "database": "connected"}

app.include_router(router, prefix="/api/v1")
