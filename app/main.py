from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.rate_limiter.instance import get_rate_limiter, set_rate_limiter
from app.core.rate_limiter.middleware import RateLimitMiddleware
from app.core.redis_client import redis_client
from app.core.rate_limiter.memory import InMemoryRateLimiter
from app.core.rate_limiter.redis import RedisRateLimiter
from app.routes import upload, evaluate, result
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.RATE_LIMIT_ENABLED:
        if settings.RATE_LIMIT_BACKEND == "memory":
            rate_limiter = InMemoryRateLimiter()
            set_rate_limiter(rate_limiter)
            print("In-Memory Rate Limiter initialized")
        elif settings.RATE_LIMIT_BACKEND == "redis":
            rate_limiter = RedisRateLimiter(redis_client)
            set_rate_limiter(rate_limiter)
            print("Redis Rate Limiter initialized")

    yield

    # Shutdown
    if settings.RATE_LIMIT_ENABLED and settings.RATE_LIMIT_BACKEND == "redis":
        # Close Redis connection if using Redis backend
        if hasattr(rate_limiter, "redis"):
            await rate_limiter.redis.close()
            print("Redis connection closed")


app = FastAPI(
    title="CV AI API",
    description="AI-powered CV and Project Evaluation System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        backend=get_rate_limiter(),
        limit=settings.RATE_LIMIT_PER_MINUTE,
        window=60,
        exclude_paths=settings.RATE_LIMIT_EXCLUDED_PATHS,
    )
    print(f"Rate Limiting enabled: {settings.RATE_LIMIT_PER_MINUTE} req/min")


# Include routers
app.include_router(upload.router)
app.include_router(evaluate.router)
app.include_router(result.router)


@app.get("/")
async def root():
    return {"message": "CV AI API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "rate_limiting": {
            "enabled": settings.RATE_LIMIT_ENABLED,
            "backend": settings.RATE_LIMIT_BACKEND
            if settings.RATE_LIMIT_ENABLED
            else None,
        },
    }
