from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from ..schemas import OrganizationCreate, OrganizationResponse
from ..db import db_client, get_tenant_db
from ..auth import decode_jwt
from ..config import settings
from ..models import OrganizationInDB, AdminInDB, TenantMetadataInDB
import re
from typing import Optional

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/login")

def sanitize_org_name(name: str) -> str:
    """Sanitizes organization name to be used as a database name."""
    # Convert to lowercase, replace spaces with underscores, remove special characters
    name = name.lower()
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^a-z0-9_]+', '', name)
    return name

async def get_current_admin_email(token: str = Depends(oauth2_scheme)) -> str:
    payload = decode_jwt(token)
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email

# Final paths are `/org/create`, `/org/get`, `/org/delete` via router prefix.
# Avoid duplicating `/org` in decorators.
@router.post("/create", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(org_create: OrganizationCreate):
    org_name_lower = sanitize_org_name(org_create.organization_name)
    
    # Check for uniqueness in master DB
    orgs_collection = db_client.get_master_db().organizations
    if await orgs_collection.find_one({"organization_name_lower": org_name_lower}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists.")

    # Hash password for admin
    from ..auth import hash_password # Import here to avoid circular dependency
    hashed_password = hash_password(org_create.password)

    # Prepare organization and admin data
    org_in_db = OrganizationInDB(
        organization_name=org_create.organization_name,
        organization_name_lower=org_name_lower,
        admin_email=org_create.email
    )

    try:
        # Insert organization metadata into master DB
        insert_result = await orgs_collection.insert_one(org_in_db.model_dump(by_alias=True))
        org_id = str(insert_result.inserted_id)

        # Create admin entry in master DB
        admins_collection = db_client.get_master_db().admins
        admin_in_db = AdminInDB(
            email=org_create.email,
            hashed_password=hashed_password,
            organization_id=org_id
        )
        await admins_collection.insert_one(admin_in_db.model_dump(by_alias=True))

        # Initialize tenant database with metadata
        tenant_db = get_tenant_db(org_name_lower)
        tenant_metadata_collection = tenant_db.tenant_metadata
        tenant_metadata = TenantMetadataInDB(
            organization_id=org_id,
            organization_name=org_create.organization_name
        )
        await tenant_metadata_collection.insert_one(tenant_metadata.model_dump(by_alias=True))

        return OrganizationResponse(
            organization_name=org_in_db.organization_name,
            admin_email=org_in_db.admin_email,
            created_at=org_in_db.created_at.isoformat()
        )
    except Exception as e:
        # Rollback: delete partially created data
        await orgs_collection.delete_one({"_id": org_id})
        await db_client.get_master_db().admins.delete_one({"email": org_create.email})
        # TODO: Ideally, drop the tenant database if it was created, but Motor doesn't have a direct drop_database
        # Might need to connect with pymongo or ensure tenant DB creation is part of a transaction if possible.
        # For now, it's safer to leave potentially empty tenant DBs and handle them manually or with a cleanup script.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create organization: {e}")


@router.get("/get", response_model=OrganizationResponse)
async def get_organization(organization_name: str):
    org_name_lower = sanitize_org_name(organization_name)
    orgs_collection = db_client.get_master_db().organizations
    org_data = await orgs_collection.find_one({"organization_name_lower": org_name_lower})

    if not org_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    
    org_in_db = OrganizationInDB(**org_data)
    return OrganizationResponse(
        organization_name=org_in_db.organization_name,
        admin_email=org_in_db.admin_email,
        created_at=org_in_db.created_at.isoformat()
    )


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(organization_name: str, admin_email: str = Depends(get_current_admin_email)):
    org_name_lower = sanitize_org_name(organization_name)
    orgs_collection = db_client.get_master_db().organizations
    org_data = await orgs_collection.find_one({"organization_name_lower": org_name_lower})

    if not org_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    
    org_in_db = OrganizationInDB(**org_data)

    if org_in_db.admin_email != admin_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this organization.")
    
    # Delete from master DB
    await orgs_collection.delete_one({"_id": org_in_db.id})
    await db_client.get_master_db().admins.delete_one({"organization_id": org_in_db.id})

    # Drop tenant database
    await db_client.client.drop_database(f"org_{org_name_lower}")

    return


class OrganizationUpdatePayload(OrganizationCreate):
    """Request payload for organization rename.
    Why: keep validation consistent with creation while providing a new name field.
    """
    new_name: str

@router.put("/update", response_model=OrganizationResponse)
async def update_organization(payload: OrganizationUpdatePayload, admin_email: str = Depends(get_current_admin_email)):
    """Rename an organization in the master DB.

    Note: This does not move tenant data. Use `scripts/migrate_org_name.py` to copy
    data to the new tenant database name, then update application config.
    """
    old_lower = sanitize_org_name(payload.organization_name)
    new_lower = sanitize_org_name(payload.new_name)

    orgs_collection = db_client.get_master_db().organizations

    # Validate target name is available
    if await orgs_collection.find_one({"organization_name_lower": new_lower}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="New organization name already exists.")

    # Fetch existing org
    existing = await orgs_collection.find_one({"organization_name_lower": old_lower})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    org_in_db = OrganizationInDB(**existing)

    # Authorization: only the org's admin may rename
    if org_in_db.admin_email != admin_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this organization.")

    # Update master metadata only; tenant DB migration is a separate step.
    await orgs_collection.update_one(
        {"_id": org_in_db.id},
        {"$set": {"organization_name": payload.new_name, "organization_name_lower": new_lower}}
    )

    return OrganizationResponse(
        organization_name=payload.new_name,
        admin_email=org_in_db.admin_email,
        created_at=org_in_db.created_at.isoformat(),
    )
