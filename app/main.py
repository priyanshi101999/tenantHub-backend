from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import router

app = FastAPI()

@app.get("/")
def greeting():
    print(settings.database_url)
    return {  "message": settings.database_url }

app.include_router(router, prefix="/api/v1")
