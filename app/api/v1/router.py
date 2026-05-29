from .endpoints import auth, user
from fastapi import APIRouter

router=APIRouter()

router.include_router(auth.router)
router.include_router(user.router)
