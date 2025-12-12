from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ..schemas import AdminLogin, Token
from ..auth import verify_password, create_jwt
from ..db import db_client
from ..config import settings
from ..models import AdminInDB
from datetime import timedelta

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/login")

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ..schemas import AdminLogin, Token
from ..auth import verify_password, create_jwt
from ..db import db_client
from ..config import settings
from ..models import AdminInDB
from datetime import timedelta

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/login")

@router.post("/login", response_model=Token)
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    admin_collection = db_client.get_master_db().admins
    admin_data = await admin_collection.find_one({"email": form_data.username})

    if not admin_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    admin_in_db = AdminInDB(**admin_data)

    if not verify_password(form_data.password, admin_in_db.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(seconds=settings.JWT_EXP_SECONDS)
    access_token = create_jwt(
        data={"sub": admin_in_db.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
