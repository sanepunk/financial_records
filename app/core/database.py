from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client = None
        self.database = None


db = Database()


async def connect_to_mongo():
    """setup database connection"""
    try:
        db.client = AsyncIOMotorClient(settings.mongodb_url)
        db.database = db.client[settings.database_name]
        
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """close database connection when shutting down"""
    if db.client:
        db.client.close()
        logger.info("MongoDB connection closed")


def get_database():
    """get the database instance"""
    return db.database
