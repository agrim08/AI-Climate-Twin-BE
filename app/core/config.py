from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file explicitly
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "ClimateTwin India"
    API_V1_STR: str = "/api/v1"
    CACHE_TTL: int = 86400  # Default cache TTL: 24 hours
    
    # CORS Origins
    # Expected formats in .env:
    # - A comma-separated string: "http://localhost:3000,http://localhost:8000"
    # - A list string: '["http://localhost:3000", "http://localhost:8000"]'
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Supabase PostgreSQL Configuration (Individual parameters)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "postgres"
    
    # Complete Connection String URL (takes precedence if provided)
    DATABASE_URL: str | None = None

    # Supabase Auth Configuration
    SUPABASE_URL: str = "https://hbujzqiprvyfefzkfzxp.supabase.co"
    SUPABASE_JWT_SECRET: str = "your-supabase-jwt-secret"  # Used to verify JWT tokens
    SUPABASE_ANON_KEY: str = "your-supabase-anon-key"      # Needed to call Supabase REST Auth signup/login

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """
        Dynamically constructs the async postgresql+asyncpg:// connection URL.
        Converts synchronous postgres:// and postgresql:// URLs automatically.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """
        Dynamically constructs the sync postgresql:// connection URL for tools like Alembic offline mode.
        """
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
