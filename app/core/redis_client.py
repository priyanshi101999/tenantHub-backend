import redis.asyncio as redis
from .config import settings

redis_client=redis.Redis(
    host=settings.redis_host,
    port=6379,
    db=1,
    decode_responses=True
)