import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Trading Battles Platform"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = secrets.token_urlsafe(32) # Generate a strong secret key
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes

    # Database settings (will be used later)
    DATABASE_URL: str = "sqlite:///./data/trading.db"

    # Mail verification settings (will be used later)
    EMAIL_SECRET_KEY: str = secrets.token_urlsafe(32)
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24


    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
