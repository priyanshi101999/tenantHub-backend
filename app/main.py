from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credencials=True

)


@app.get("/")
def greeting():
    print(settings.database_url)
    return {  "message": settings.database_url }

app.include_router(router, prefix="/api/v1")
