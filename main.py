
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api import api_router
import time

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Contract Intelligence Parser API")
    await connect_to_mongo()
    yield
    logger.info("Shutting down Contract Intelligence Parser API")
    await close_mongo_connection()

app = FastAPI(
    title="Contract Intelligence Parser API",
    description="AI-powered contract analysis and data extraction system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Contract Intelligence Parser API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    time_now = time.time()
    time_string = time.strftime("Date: %d:%m:%Y Time: %H:%M:%S", time.localtime(time_now))
    return {
        "status": "healthy",
        "database": "connected",
        "api_version": "1.0.0",
        "time": time_string,
        "env": "Online" if settings else "Offline"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
