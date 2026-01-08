from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Trading Battles Platform"
    API_V1_STR: str = "/api/v1"

    # Use a stable secret key - override in .env for production!
    SECRET_KEY: str = "dev-secret-key-CHANGE-IN-PRODUCTION"
    ALGORITHM: str = "HS256"  # JWT signing algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes

    # Database settings (will be used later)
    DATABASE_URL: str = "sqlite:///./data/trading.db"

    # Mail verification settings (will be used later)
    EMAIL_SECRET_KEY: str = "dev-email-secret-CHANGE-IN-PRODUCTION"
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24


    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
