import pytest
from httpx import AsyncClient
from ..app.main import app
from ..app.db import db_client, get_tenant_db
from ..app.config import settings
from ..app.auth import hash_password
from ..app.routers.orgs import sanitize_org_name

# Use a test database
TEST_MASTER_DB = "test_master_db"
settings.MASTER_DB = TEST_MASTER_DB
settings.MONGO_URI = "mongodb://localhost:27017" # Ensure this points to a local test MongoDB

@pytest.fixture(scope="module", autouse=True)
async def setup_and_teardown_db():
    """Fixture to set up and tear down the database for tests."""
    print("Setting up test database...")
    await db_client.connect()
    
    # Ensure master DB is clean
    await db_client.get_master_db().command("dropDatabase")

    # Create a test admin for login
    admin_email = "testadmin@example.com"
    hashed_pass = hash_password("testpassword")
    
    # We need an organization ID for the admin, let's create a dummy one
    dummy_org_id = "dummy_org_id_for_admin"

    await db_client.get_master_db().admins.insert_one({
        "email": admin_email,
        "hashed_password": hashed_pass,
        "organization_id": dummy_org_id # This admin isn't directly tied to a full org creation for this test
    })
    
    yield # Run the tests

    print("Tearing down test database...")
    await db_client.get_master_db().command("dropDatabase")
    await db_client.close()


@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="module")
async def admin_token(client: AsyncClient):
    """Fixture to get an admin JWT token."""
    response = await client.post(
        "/admin/login",
        data={"username": "testadmin@example.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "env": "development"}

@pytest.mark.asyncio
async def test_create_organization(client: AsyncClient):
    org_data = {
        "organization_name": "Test Org",
        "email": "orgadmin@example.com",
        "password": "orgpassword123"
    }
    response = await client.post("/org/create", json=org_data)
    assert response.status_code == 201
    json_response = response.json()
    assert json_response["organization_name"] == "Test Org"
    assert json_response["admin_email"] == "orgadmin@example.com"
    assert "created_at" in json_response

    # Verify in master DB
    org_in_db = await db_client.get_master_db().organizations.find_one({"organization_name_lower": "test_org"})
    assert org_in_db is not None
    assert org_in_db["organization_name"] == "Test Org"
    
    # Verify admin in master DB
    admin_in_db = await db_client.get_master_db().admins.find_one({"email": "orgadmin@example.com"})
    assert admin_in_db is not None
    assert admin_in_db["organization_id"] == str(org_in_db["_id"])

    # Verify tenant DB metadata
    tenant_db = get_tenant_db("test_org")
    metadata = await tenant_db.tenant_metadata.find_one({"organization_id": str(org_in_db["_id"])})
    assert metadata is not None
    assert metadata["organization_name"] == "Test Org"

@pytest.mark.asyncio
async def test_create_organization_duplicate_name(client: AsyncClient):
    org_data = {
        "organization_name": "Test Org", # Duplicate name
        "email": "anotheradmin@example.com",
        "password": "password123"
    }
    response = await client.post("/org/create", json=org_data)
    assert response.status_code == 409
    assert response.json()["detail"] == "Organization name already exists."

@pytest.mark.asyncio
async def test_get_organization(client: AsyncClient):
    response = await client.get("/org/get?organization_name=Test%20Org")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["organization_name"] == "Test Org"
    assert json_response["admin_email"] == "orgadmin@example.com"

@pytest.mark.asyncio
async def test_get_non_existent_organization(client: AsyncClient):
    response = await client.get("/org/get?organization_name=NonExistentOrg")
    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found."

@pytest.mark.asyncio
async def test_delete_organization_unauthorized(client: AsyncClient):
    response = await client.delete("/org/delete?organization_name=Test%20Org")
    assert response.status_code == 401 # No token

@pytest.mark.asyncio
async def test_delete_organization_wrong_admin(client: AsyncClient, admin_token: str):
    # Try to delete with an admin token that is not the org's admin
    response = await client.delete(
        "/org/delete?organization_name=Test%20Org",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to delete this organization."


@pytest.mark.asyncio
async def test_delete_organization(client: AsyncClient):
    # First, create another organization with a different admin so we can log in as that admin
    org_name_to_delete = "OrgToDelete"
    admin_email_to_delete = "deleteadmin@example.com"
    org_data = {
        "organization_name": org_name_to_delete,
        "email": admin_email_to_delete,
        "password": "deletepassword123"
    }
    response = await client.post("/org/create", json=org_data)
    assert response.status_code == 201

    # Log in as the admin for OrgToDelete
    response = await client.post(
        "/admin/login",
        data={"username": admin_email_to_delete, "password": "deletepassword123"}
    )
    assert response.status_code == 200
    delete_token = response.json()["access_token"]

    # Now delete with the correct token
    response = await client.delete(
        f"/org/delete?organization_name={org_name_to_delete}",
        headers={"Authorization": f"Bearer {delete_token}"}
    )
    assert response.status_code == 204

    # Verify it's deleted from master DB
    org_in_db = await db_client.get_master_db().organizations.find_one({"organization_name_lower": sanitize_org_name(org_name_to_delete)})
    assert org_in_db is None

    # Verify admin is deleted
    admin_in_db = await db_client.get_master_db().admins.find_one({"email": admin_email_to_delete})
    assert admin_in_db is None

    # Verify tenant DB is dropped (by trying to access a collection, which should fail or return None)
    db_names = await db_client.client.list_database_names()
    assert f"org_{sanitize_org_name(org_name_to_delete)}" not in db_names
