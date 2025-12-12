from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import datetime

class OrganizationInDB(BaseModel):
    id: Optional[str] = Field(alias='_id', default=None)
    organization_name: str
    organization_name_lower: str
    admin_email: EmailStr
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class AdminInDB(BaseModel):
    id: Optional[str] = Field(alias='_id', default=None)
    email: EmailStr
    hashed_password: str
    organization_id: str # Link to the organization
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class TenantMetadataInDB(BaseModel):
    # This document will be stored in each tenant database to identify it
    id: Optional[str] = Field(alias='_id', default=None)
    organization_id: str
    organization_name: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
