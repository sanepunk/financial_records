# Core configuration and database
from .config import settings
from .database import get_database, connect_to_mongo, close_mongo_connection
