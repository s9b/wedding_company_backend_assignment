import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
import datetime
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

class AdminCreate(BaseModel):
    email: EmailStr
    password: str

async def create_admin_user(mongo_uri: str, master_db_name: str, admin_email: str, admin_password: str):
    client = AsyncIOMotorClient(mongo_uri)
    db = client[master_db_name]
    admins_collection = db.admins

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(admin_password)

    dummy_organization_id = "system_admin_org" # Placeholder

    admin_data = {
        "email": admin_email,
        "hashed_password": hashed_password,
        "organization_id": dummy_organization_id,
        "created_at": datetime.datetime.utcnow(),
    }

    try:
        if await admins_collection.find_one({"email": admin_email}):
            print(f"Admin user '{admin_email}' already exists. Skipping creation.")
        else:
            await admins_collection.insert_one(admin_data)
            print(f"Admin user '{admin_email}' created successfully.")
    except Exception as e:
        print(f"Error creating admin user '{admin_email}': {e}")
    finally:
        client.close()

if __name__ == "__main__":
    MONGO_URI = os.getenv("MONGO_URI")
    MASTER_DB = os.getenv("MASTER_DB", "master")

    if not MONGO_URI:
        print("MONGO_URI environment variable not set in .env. Please configure it.")
        exit(1)

    ADMIN_EMAIL = "admin@example.com"
    ADMIN_PASSWORD = "password123" 

    print(f"Attempting to create admin '{ADMIN_EMAIL}' in master DB '{MASTER_DB}'...")
    asyncio.run(create_admin_user(MONGO_URI, MASTER_DB, ADMIN_EMAIL, ADMIN_PASSWORD))
