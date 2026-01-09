from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Mockstreet"
    API_V1_STR: str = "/api/v1"

    # Use a stable secret key - override in .env for production!
    SECRET_KEY: str = "dev-secret-key-CHANGE-IN-PRODUCTION"
    ALGORITHM: str = "HS256"  # JWT signing algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes

    # Database settings (will be used later)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:StrongPassword123@localhost/mockstreet"

    # Mail verification settings (will be used later)
    EMAIL_SECRET_KEY: str = "dev-email-secret-CHANGE-IN-PRODUCTION"
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    
    # Email / SMTP Settings
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = "smtp.gmail.com"
    SMTP_USER: str | None = "mockstreetgames@gmail.com"
    SMTP_PASSWORD: str | None = "xrjj dqxl nppq pkvd"
    EMAILS_FROM_EMAIL: str | None = "mockstreetgames@gmail.com"
    EMAILS_FROM_NAME: str | None = "Mockstreet"
    
    # Frontend URL for links
    FRONTEND_URL: str = "https://mockstreet.com"


    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
