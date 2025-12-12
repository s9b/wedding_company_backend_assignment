import argparse
import asyncio
import os
import re
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from hashlib import sha256

def sanitize_name(name: str) -> str:
    """Sanitizes organization name to be used as a database name."""
    name = name.lower()
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^a-z0-9_]+', '', name)
    return name

async def migrate_org_name(
    mongo_uri: str, old_org_name: str, new_org_name: str, batch_size: int = 100
):
    print(f"Starting migration from '{old_org_name}' to '{new_org_name}'...")

    old_org_name_sanitized = sanitize_name(old_org_name)
    new_org_name_sanitized = sanitize_name(new_org_name)

    if old_org_name_sanitized == new_org_name_sanitized:
        print("Sanitized old and new organization names are the same. No migration needed.")
        return

    old_db_name = f"org_{old_org_name_sanitized}"
    new_db_name = f"org_{new_org_name_sanitized}"

    client = AsyncIOMotorClient(mongo_uri)
    
    # Check if old database exists
    db_names = await client.list_database_names()
    if old_db_name not in db_names:
        print(f"Error: Old database '{old_db_name}' does not exist.")
        await client.close()
        return

    # Check if new database already exists
    if new_db_name in db_names:
        print(f"Warning: New database '{new_db_name}' already exists. Merging/resuming migration.")
        # Optionally, add logic here to compare and handle conflicts if merging, or resume if just copying missing docs
    
    old_db = client[old_db_name]
    new_db = client[new_db_name]

    old_collections = await old_db.list_collection_names()
    print(f"Collections in old database '{old_db_name}': {old_collections}")

    for collection_name in old_collections:
        print(f"Migrating collection: {collection_name}")
        old_collection = old_db[collection_name]
        new_collection = new_db[collection_name]

        copied_count = 0
        skipped_count = 0
        total_documents_old = await old_collection.count_documents({})
        
        # Cursor for batch processing
        cursor = old_collection.find({}, no_cursor_timeout=True) # no_cursor_timeout to prevent cursor expiration
        
        batch = []
        async for document in cursor:
            # Check if document already exists in new collection (for resuming)
            if await new_collection.count_documents({"_id": document["_id"]}) > 0:
                skipped_count += 1
                continue
            
            batch.append(document)
            if len(batch) >= batch_size:
                await new_collection.insert_many(batch)
                copied_count += len(batch)
                batch = []
                print(f"  Copied {copied_count}/{total_documents_old} documents for '{collection_name}'...")
        
        if batch: # Insert any remaining documents
            await new_collection.insert_many(batch)
            copied_count += len(batch)

        print(f"Finished copying collection '{collection_name}'. Copied: {copied_count}, Skipped (already exists): {skipped_count}")

        # Verification
        new_count = await new_collection.count_documents({})
        if new_count != (total_documents_old - skipped_count): # Adjusted for skipped documents
            print(f"  WARNING: Count mismatch for '{collection_name}'! Old: {total_documents_old}, New: {new_count}")
        else:
            print(f"  Count verification successful for '{collection_name}'. Total documents: {new_count}")

        # Sample hash verification (simple hash of a few documents)
        sample_docs_old = await old_collection.find().limit(5).to_list(length=5)
        sample_docs_new = await new_collection.find().limit(5).to_list(length=5)

        old_hash = sha256(str(sample_docs_old).encode()).hexdigest()
        new_hash = sha256(str(sample_docs_new).encode()).hexdigest()

        if old_hash != new_hash:
            print(f"  WARNING: Sample hash mismatch for '{collection_name}'! Data integrity might be compromised.")
        else:
            print(f"  Sample hash verification successful for '{collection_name}'.")
    
    await client.close()

    print("\n--- MIGRATION COMPLETE ---")
    print(f"Old database: '{old_db_name}'")
    print(f"New database: '{new_db_name}'")
    print("\nMANUAL CUTOVER STEPS:")
    print("1. **VERIFY DATA:** Thoroughly inspect the new database to ensure all data has been copied correctly and is accessible.")
    print(f"   E.g., connect to MongoDB and run `use {new_db_name}; db.collection.find().limit(10);`")
    print("2. **UPDATE APPLICATION CONFIGURATION:** Change your application's configuration to point to the new organization name (and thus the new database).")
    print("3. **TEST APPLICATION:** Deploy and thoroughly test your application with the new configuration.")
    print(f"4. **CONSIDER DELETION (CAUTION!):** Once you are absolutely certain that the new database '{new_db_name}' is working as expected and the old database '{old_db_name}' is no longer needed, you can manually drop the old database.")
    print(f"   Example command in MongoDB shell: `use {old_db_name}; db.dropDatabase();`")
    print("   **DO NOT DELETE THE OLD DATABASE UNTIL YOU ARE 100% CONFIDENT IN THE NEW ONE.**")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate an organization's tenant database to a new name.")
    parser.add_argument("--mongo-uri", required=True, help="MongoDB connection URI.")
    parser.add_argument("--old", required=True, help="Old organization name.")
    parser.add_argument("--new", required=True, help="New organization name.")
    parser.add_argument("--batch", type=int, default=100, help="Batch size for copying documents.")

    args = parser.parse_args()
    
    # Set up environment variables if .env exists
    from dotenv import load_dotenv
    load_dotenv()

    # If MONGO_URI is not provided as CLI arg, try to get it from environment
    if not args.mongo_uri and os.getenv("MONGO_URI"):
        args.mongo_uri = os.getenv("MONGO_URI")
    
    if not args.mongo_uri:
        print("Error: MongoDB URI not provided. Use --mongo-uri or set MONGO_URI environment variable.")
        exit(1)

    asyncio.run(migrate_org_name(args.mongo_uri, args.old, args.new, args.batch))
