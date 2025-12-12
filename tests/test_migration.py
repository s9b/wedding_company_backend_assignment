import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from scripts.migrate_org_name import migrate_org_name, sanitize_name


@pytest.mark.asyncio
async def test_migration_dry_run_copy_and_preserve():
    mongo_uri = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(mongo_uri)

    old_name = "Mig Old"
    new_name = "Mig New"
    old_db = client[f"org_{sanitize_name(old_name)}"]
    new_db = client[f"org_{sanitize_name(new_name)}"]

    # Ensure clean state
    await client.drop_database(old_db.name)
    await client.drop_database(new_db.name)

    # Seed source DB with a collection and document
    await old_db.test_collection.insert_one({"_id": 1, "value": "a"})

    # Run migration
    await migrate_org_name(mongo_uri, old_name, new_name, batch_size=10)

    # Verify copy happened
    doc_new = await new_db.test_collection.find_one({"_id": 1})
    assert doc_new is not None
    assert doc_new["value"] == "a"

    # Verify source DB preserved
    doc_old = await old_db.test_collection.find_one({"_id": 1})
    assert doc_old is not None

    # Cleanup
    await client.drop_database(old_db.name)
    await client.drop_database(new_db.name)
    client.close()
