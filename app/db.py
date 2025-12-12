from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

class MongoClient:
    client: AsyncIOMotorClient = None
    
    async def connect(self):
        if self.client is None:
            self.client = AsyncIOMotorClient(settings.MONGO_URI)
            print("MongoDB connection established.")

    async def close(self):
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")

    def get_database(self, db_name: str):
        if self.client is None:
            raise Exception("MongoDB client not initialized. Call connect() first.")
        return self.client[db_name]

    def get_master_db(self):
        return self.get_database(settings.MASTER_DB)

db_client = MongoClient()

# Helper function to get a tenant database
def get_tenant_db(org_name_lower: str):
    # Tenant databases are prefixed with 'org_'
    tenant_db_name = f"org_{org_name_lower}"
    return db_client.get_database(tenant_db_name)
