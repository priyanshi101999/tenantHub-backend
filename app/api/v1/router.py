from .endpoints import auth
from fastapi import APIRouter

router=APIRouter(tags=["Authentication"])

router.include_router(auth.router)
