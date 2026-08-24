import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR.parent / "uploads"
OUTPUT_DIR = BASE_DIR.parent / "outputs"
TEMPLATE_DIR = BASE_DIR.parent / "templates"
SAMPLE_DIR = BASE_DIR.parent / "sample_data"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "AI PDF to Excel Quotation Converter"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".xlsx", ".xlsm"}
    TEMP_EXPIRATION_HOURS: int = 24


settings = Settings()
