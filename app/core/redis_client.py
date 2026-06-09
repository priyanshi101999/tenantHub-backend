import redis.asyncio as redis
from .config import settings

if settings.redis_url:
    redis_client = redis.from_url(
        settings.redis_url,
        db=1,
        decode_responses=True
    )
else:
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=1,
        decode_responses=True
    )
