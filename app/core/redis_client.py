from redis.asyncio import Redis
from app.config import settings

redis_client = Redis.from_url(
    url=settings.REDIS_URL, encoding="utf-8", decode_responses=True
)
