from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class OrganizationCreate(BaseModel):
    organization_name: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8) # TODO: Add more password complexity rules

class OrganizationResponse(BaseModel):
    organization_name: str
    admin_email: EmailStr
    created_at: str # Will be formatted to ISO string for response

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[EmailStr] = None

