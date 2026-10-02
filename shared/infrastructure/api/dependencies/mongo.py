from motor.motor_asyncio import AsyncIOMotorDatabase

from shared.infrastructure.persistence.mongo.database import mongo_manager


def get_mongo_db() -> AsyncIOMotorDatabase:
    return mongo_manager.get_database()
