from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api import api_router

# setup logging with proper format
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup stuff
    logger.info("Starting up Contract Intelligence Parser API")
    await connect_to_mongo()
    yield
    # shutdown stuff
    logger.info("Shutting down Contract Intelligence Parser API")
    await close_mongo_connection()


# create the fastapi app
app = FastAPI(
    title="Contract Intelligence Parser API",
    description="AI-powered contract analysis and data extraction system",
    version="1.0.0",
    lifespan=lifespan
)

# cors middleware - allow all origins for now (change for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include the api routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """basic health check endpoint"""
    return {
        "message": "Contract Intelligence Parser API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """more detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "api_version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
