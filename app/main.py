from fastapi import FastAPI
from dotenv import load_dotenv
import os
from .db import db_client
from .routers import admin, orgs

load_dotenv()

app = FastAPI()

@app.on_event("startup")
async def startup_db_client():
    await db_client.connect()

@app.on_event("shutdown")
async def shutdown_db_client():
    await db_client.close()

@app.get("/health")
async def health_check():
    return {"status": "ok", "env": os.getenv("ENV", "development")}

app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(orgs.router, prefix="/org", tags=["organization"])