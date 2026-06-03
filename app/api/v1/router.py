from .endpoints import auth, user, task, stripe
from fastapi import APIRouter

router=APIRouter()

router.include_router(auth.router)
router.include_router(user.router)
router.include_router(task.router)
router.include_router(stripe.router)
