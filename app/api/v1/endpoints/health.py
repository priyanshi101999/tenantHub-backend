from fastapi import APIRouter, Depends, status, HTTPException
from app.api.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router=APIRouter()

@router.get("/health")
async def health_check(db:AsyncSession=Depends(get_db)):
    try:
        await db.execute(select(1))
        return {"status": "healthy"}
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unhealthy")

    

