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


import json

def _load_self_client_creds() -> tuple[str, str, str, str]:
    """Helper to safely read client_id, client_secret, authorization code, and refresh_token if present."""
    search_paths = [
        BASE_DIR.parent / "zoho_tokens.json",
        BASE_DIR / "zoho_tokens.json",
        BASE_DIR.parent / "self_client.json",
        BASE_DIR / "self_client.json",
        Path.home() / "Downloads" / "self_client.json",
    ]
    client_id, client_secret, code, refresh = "", "", "", ""
    for p in search_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not client_id:
                        client_id = (
                            data.get("client_id")
                            or data.get("installed", {}).get("client_id")
                            or data.get("web", {}).get("client_id")
                            or ""
                        )
                    if not client_secret:
                        client_secret = (
                            data.get("client_secret")
                            or data.get("client_secret_id")
                            or data.get("installed", {}).get("client_secret")
                            or data.get("web", {}).get("client_secret")
                            or ""
                        )
                    if not code:
                        code = data.get("code") or data.get("grant_token") or ""
                    if not refresh:
                        refresh = data.get("refresh_token") or ""
            except Exception:
                pass
    return str(client_id).strip(), str(client_secret).strip(), str(code).strip(), str(refresh).strip()


_sc_id, _sc_secret, _sc_grant, _sc_refresh = _load_self_client_creds()


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

    # Zoho Books Configuration
    ZOHO_BOOKS_ORGANIZATION_ID: str = os.getenv("ZOHO_BOOKS_ORGANIZATION_ID", os.getenv("ZOHO_ORG_ID", "741367552"))
    ZOHO_BOOKS_CLIENT_ID: str = os.getenv("ZOHO_BOOKS_CLIENT_ID", os.getenv("ZOHO_CLIENT_ID", _sc_id))
    ZOHO_BOOKS_CLIENT_SECRET: str = os.getenv("ZOHO_BOOKS_CLIENT_SECRET", os.getenv("ZOHO_CLIENT_SECRET", _sc_secret))
    ZOHO_BOOKS_GRANT_TOKEN: str = os.getenv("ZOHO_BOOKS_GRANT_TOKEN", _sc_grant)
    ZOHO_BOOKS_REFRESH_TOKEN: str = os.getenv("ZOHO_BOOKS_REFRESH_TOKEN", os.getenv("ZOHO_REFRESH_TOKEN", _sc_refresh))
    ZOHO_BOOKS_ACCOUNTS_URL: str = os.getenv("ZOHO_BOOKS_ACCOUNTS_URL", "https://accounts.zoho.com")
    ZOHO_BOOKS_API_DOMAIN: str = os.getenv("ZOHO_BOOKS_API_DOMAIN", "https://www.zohoapis.com")
    ZOHO_CONNECTION_NAME: str = os.getenv("ZOHO_CONNECTION_NAME", "zoho_books_automation")

    # Backwards-compatibility aliases
    @property
    def ZOHO_ORG_ID(self) -> str:
        return self.ZOHO_BOOKS_ORGANIZATION_ID

    @property
    def ZOHO_REFRESH_TOKEN(self) -> str:
        return self.ZOHO_BOOKS_REFRESH_TOKEN

    @property
    def ZOHO_API_DOMAIN(self) -> str:
        return f"{self.ZOHO_BOOKS_API_DOMAIN.rstrip('/')}/books/v3/"

    @property
    def ZOHO_CLIENT_ID(self) -> str:
        return self.ZOHO_BOOKS_CLIENT_ID

    @property
    def ZOHO_CLIENT_SECRET(self) -> str:
        return self.ZOHO_BOOKS_CLIENT_SECRET


settings = Settings()
