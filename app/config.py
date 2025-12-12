from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    MONGO_URI: str = Field(..., description="MongoDB connection URI")
    MASTER_DB: str = Field("master", description="Name of the master database")
    JWT_SECRET: str = Field(..., description="Secret key for JWT encoding/decoding")
    JWT_EXP_SECONDS: int = Field(3600, description="JWT expiration time in seconds")
    ENV: str = Field("development", description="Application environment (e.g., development, production)")

settings = Settings()
