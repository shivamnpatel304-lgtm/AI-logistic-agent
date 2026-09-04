"""
Application Configuration Settings.
Loads configuration from environment variables and .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")


class Settings:
    # General Settings
    APP_NAME: str = os.getenv("APP_NAME", "AI Logistics Agent")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./logistics.db")

    # AI / LLM Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    ENABLE_LLM_AGENT: bool = os.getenv("ENABLE_LLM_AGENT", "False").lower() in ("true", "1", "t")

    # Logistics & Allocation Business Defaults
    DEFAULT_MAX_DELIVERY_RADIUS_KM: float = float(os.getenv("DEFAULT_MAX_DELIVERY_RADIUS_KM", "500.0"))
    HIGH_VALUE_ORDER_THRESHOLD: float = float(os.getenv("HIGH_VALUE_ORDER_THRESHOLD", "10000.0"))
    SAFETY_STOCK_DEFAULT: int = int(os.getenv("SAFETY_STOCK_DEFAULT", "20"))


settings = Settings()
