from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import upload, evaluate, result

app = FastAPI(
    title="CV AI API",
    description="AI-powered CV and Project Evaluation System",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(evaluate.router)
app.include_router(result.router)


@app.get("/")
async def root():
    return {"message": "CV AI API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
