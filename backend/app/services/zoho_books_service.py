import os
import time
import json
import logging
from pathlib import Path
from typing import Optional, Any
import httpx

from app.config import settings, BASE_DIR

logger = logging.getLogger(__name__)

# Token cache file location (secured and added to .gitignore)
TOKEN_CACHE_FILE = Path(os.getenv("ZOHO_TOKEN_CACHE_PATH", str(BASE_DIR.parent / "zoho_tokens.json")))

# Mandatory Test Item Specification
TEST_AUTOMATION_SKU = "TEST-AUTOMATION-001"
TEST_AUTOMATION_ITEM_ID = "2552396000020372001"



class ZohoTokenManager:
    """Manages Zoho Books OAuth tokens, automatic exchange and refresh without logging sensitive secrets."""

    def __init__(self):
        self.accounts_url = settings.ZOHO_BOOKS_ACCOUNTS_URL.rstrip("/")
        self.api_domain = settings.ZOHO_BOOKS_API_DOMAIN.rstrip("/")
        self.organization_id = settings.ZOHO_BOOKS_ORGANIZATION_ID
        self.client_id = settings.ZOHO_BOOKS_CLIENT_ID
        self.client_secret = settings.ZOHO_BOOKS_CLIENT_SECRET
        self.grant_token = settings.ZOHO_BOOKS_GRANT_TOKEN

        # Dynamic fallback to self_client.json if any credential is unset
        if not (self.client_id and self.client_secret and self.grant_token):
            search_paths = [
                BASE_DIR.parent / "self_client.json",
                BASE_DIR / "self_client.json",
                Path.home() / "Downloads" / "self_client.json",
            ]
            for p in search_paths:
                if p.exists():
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            sc_data = json.load(f)
                            if not self.client_id:
                                self.client_id = sc_data.get("client_id") or sc_data.get("installed", {}).get("client_id") or ""
                            if not self.client_secret:
                                self.client_secret = sc_data.get("client_secret") or sc_data.get("client_secret_id") or sc_data.get("installed", {}).get("client_secret") or ""
                            if not self.grant_token:
                                self.grant_token = sc_data.get("code") or sc_data.get("grant_token") or ""
                    except Exception:
                        pass

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float = 0.0
        self._token_api_domain: Optional[str] = None

        self._load_cached_tokens()

    def _load_cached_tokens(self) -> None:
        """Loads cached tokens from zoho_tokens.json if present."""
        if TOKEN_CACHE_FILE.exists():
            try:
                with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._access_token = data.get("access_token")
                    self._refresh_token = data.get("refresh_token")
                    self._expires_at = float(data.get("expires_at", 0.0))
                    self._token_api_domain = data.get("api_domain")
            except Exception as e:
                logger.warning(f"Could not load cached tokens: {e}")

    def _save_cached_tokens(self) -> None:
        """Saves current tokens to zoho_tokens.json without ever logging them."""
        if not getattr(self, "persist_tokens", True):
            return
        if self._access_token and self._access_token.startswith("mock_"):
            return
        try:
            payload = {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "expires_at": self._expires_at,
                "api_domain": self._token_api_domain or self.api_domain,
                "updated_at": time.time(),
            }
            with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not cache tokens to file: {e}")

    def get_effective_api_domain(self) -> str:
        return self._token_api_domain or self.api_domain

    def is_configured(self) -> bool:
        """Checks if client credentials are available."""
        return bool(self.client_id and self.client_secret)

    def exchange_grant_token(self, code: Optional[str] = None) -> dict[str, Any]:
        """
        Exchanges an authorization code (grant token) for access_token and refresh_token.
        POST {accounts_url}/oauth/v2/token
        grant_type=authorization_code
        client_id=...
        client_secret=...
        code=...
        """
        grant_code = code or self.grant_token
        if not grant_code:
            raise ValueError("No grant token (authorization code) provided or configured.")
        if not self.is_configured():
            raise ValueError("Zoho Books client_id and client_secret must be configured.")

        url = f"{self.accounts_url}/oauth/v2/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": grant_code,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, data=data)
                res_data = res.json()

            if "error" in res_data:
                err_msg = res_data.get("error", "OAuth exchange failed")
                logger.error(f"Zoho OAuth exchange error: {err_msg}")
                return {"success": False, "error": err_msg}

            access_token = res_data.get("access_token")
            refresh_token = res_data.get("refresh_token")
            expires_in = res_data.get("expires_in", 3600)
            api_domain = res_data.get("api_domain")

            if not access_token:
                return {"success": False, "error": "No access_token returned by Zoho."}

            self._access_token = access_token
            if refresh_token:
                self._refresh_token = refresh_token
            self._expires_at = time.time() + float(expires_in)
            if api_domain:
                self._token_api_domain = api_domain

            self._save_cached_tokens()
            logger.info("Zoho OAuth grant token successfully exchanged for access/refresh tokens.")
            return {
                "success": True,
                "has_refresh_token": bool(self._refresh_token),
                "expires_in": expires_in,
                "api_domain": self.get_effective_api_domain(),
            }
        except Exception as e:
            logger.error(f"Exception during Zoho grant exchange: {str(e)}")
            return {"success": False, "error": str(e)}

    def refresh_access_token(self) -> dict[str, Any]:
        """
        Uses the refresh token to obtain a fresh access token automatically.
        POST {accounts_url}/oauth/v2/token
        grant_type=refresh_token
        client_id=...
        client_secret=...
        refresh_token=...
        """
        if not self._refresh_token:
            raise ValueError("No refresh token available to refresh access token.")
        if not self.is_configured():
            raise ValueError("Zoho Books client_id and client_secret must be configured.")

        url = f"{self.accounts_url}/oauth/v2/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._refresh_token,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, data=data)
                res_data = res.json()

            if "error" in res_data:
                err_msg = res_data.get("error", "Token refresh failed")
                logger.error(f"Zoho OAuth refresh error: {err_msg}")
                return {"success": False, "error": err_msg}

            access_token = res_data.get("access_token")
            expires_in = res_data.get("expires_in", 3600)
            api_domain = res_data.get("api_domain")

            if not access_token:
                return {"success": False, "error": "No access_token returned by Zoho."}

            self._access_token = access_token
            self._expires_at = time.time() + float(expires_in)
            if api_domain:
                self._token_api_domain = api_domain

            self._save_cached_tokens()
            logger.info("Zoho access token refreshed successfully.")
            return {
                "success": True,
                "expires_in": expires_in,
                "api_domain": self.get_effective_api_domain(),
            }
        except Exception as e:
            logger.error(f"Exception during Zoho token refresh: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_valid_access_token(self) -> Optional[str]:
        """
        Returns a valid access token. Automatically refreshes if expired.
        If a grant token is configured but no refresh token yet, tries exchange.
        """
        # Buffer of 60 seconds before actual expiration
        if self._access_token and (time.time() + 60.0) < self._expires_at:
            return self._access_token

        # Try refresh if refresh_token is present
        if self._refresh_token and self.is_configured():
            res = self.refresh_access_token()
            if res.get("success"):
                return self._access_token

        # Try exchange if grant token is present
        if self.grant_token and self.is_configured():
            res = self.exchange_grant_token()
            if res.get("success"):
                return self._access_token

        return None

    def get_status_summary(self) -> dict[str, Any]:
        """Returns non-sensitive connectivity configuration status."""
        has_token = bool(self._access_token and (time.time() + 60.0) < self._expires_at)
        return {
            "organization_id": self.organization_id,
            "has_client_id": bool(self.client_id),
            "has_secret_configured": bool(self.client_secret),
            "has_grant_code": bool(self.grant_token),
            "has_refresh_flow": bool(self._refresh_token),
            "is_authenticated": has_token,
            "api_domain": self.get_effective_api_domain(),
            "accounts_url": self.accounts_url,
        }


class ZohoBooksService:
    """Service handling read-only Zoho Books operations and connectivity verification."""

    def __init__(self):
        self.token_manager = ZohoTokenManager()

    def search_items(
        self,
        search_text: str,
        organization_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Search Zoho Books Items using:
        GET https://www.zohoapis.com/books/v3/items?organization_id={organization_id}&search_text={search_text}
        Uses ONLY the real Zoho Books API. NEVER falls back to mock or hardcoded catalog data.
        """
        org_id = organization_id or self.token_manager.organization_id
        search_term = (search_text or "").strip()

        token = self.token_manager.get_valid_access_token()
        if not token:
            if self.token_manager.grant_token and self.token_manager.is_configured():
                ex_res = self.token_manager.exchange_grant_token()
                if ex_res.get("success"):
                    token = self.token_manager.get_valid_access_token()

        if token:
            api_base = self.token_manager.get_effective_api_domain().rstrip("/")
            url = f"{api_base}/books/v3/items"
            headers = {
                "Authorization": f"Zoho-oauthtoken {token}",
            }
            params = {
                "organization_id": org_id,
                "search_text": search_term,
            }

            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(url, headers=headers, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("items", [])
                        return {
                            "success": True,
                            "source": "live_zoho_api",
                            "organization_id": org_id,
                            "search_text": search_term,
                            "items": items,
                            "count": len(items),
                        }
                    elif resp.status_code == 401:
                        # Try one refresh and retry
                        ref_res = self.token_manager.refresh_access_token()
                        if ref_res.get("success"):
                            new_token = self.token_manager.get_valid_access_token()
                            headers["Authorization"] = f"Zoho-oauthtoken {new_token}"
                            retry_resp = client.get(url, headers=headers, params=params)
                            if retry_resp.status_code == 200:
                                data = retry_resp.json()
                                items = data.get("items", [])
                                return {
                                    "success": True,
                                    "source": "live_zoho_api",
                                    "organization_id": org_id,
                                    "search_text": search_term,
                                    "items": items,
                                    "count": len(items),
                                }
                        logger.warning(f"Zoho Books API authentication error (HTTP {resp.status_code})")
                    else:
                        logger.warning(f"Zoho Books API returned status {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Live Zoho API search request failed: {str(e)}")

        # No mock catalog fallback; return empty live result
        return {
            "success": False,
            "source": "live_zoho_api",
            "organization_id": org_id,
            "search_text": search_term,
            "items": [],
            "count": 0,
        }

    def list_composite_items(
        self,
        organization_id: Optional[str] = None,
        search_text: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Retrieves Composite Items from Zoho Books API (Read-Only):
        GET https://www.zohoapis.com/books/v3/compositeitems?organization_id={org_id}
        """
        org_id = organization_id or self.token_manager.organization_id
        token = self.token_manager.get_valid_access_token()
        if not token:
            if self.token_manager.grant_token and self.token_manager.is_configured():
                ex_res = self.token_manager.exchange_grant_token()
                if ex_res.get("success"):
                    token = self.token_manager.get_valid_access_token()

        if not token:
            return {
                "success": False,
                "http_status": 401,
                "error": "No valid Zoho access token available.",
                "composite_items": [],
                "count": 0,
            }

        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/compositeitems"
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        params: dict[str, Any] = {"organization_id": org_id}
        if search_text:
            params["search_text"] = search_text.strip()

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code == 401 and self.token_manager._refresh_token:
                    ref_res = self.token_manager.refresh_access_token()
                    if ref_res.get("success"):
                        token = self.token_manager.get_valid_access_token()
                        headers["Authorization"] = f"Zoho-oauthtoken {token}"
                        resp = client.get(url, headers=headers, params=params)

                data = {}
                try:
                    data = resp.json()
                except Exception:
                    pass

                items = data.get("composite_items", [])
                return {
                    "success": resp.status_code == 200 and data.get("code") == 0,
                    "http_status": resp.status_code,
                    "code": data.get("code"),
                    "message": data.get("message"),
                    "composite_items": items,
                    "count": len(items),
                }
        except Exception as e:
            return {
                "success": False,
                "http_status": 500,
                "error": str(e),
                "composite_items": [],
                "count": 0,
            }

    def get_composite_item(
        self,
        composite_item_id: str,
        organization_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fetches full details of a single composite item including constituent mapped_items:
        GET https://www.zohoapis.com/books/v3/compositeitems/{composite_item_id}?organization_id={org_id}
        """
        clean_id = str(composite_item_id or "").strip()
        if not clean_id or not clean_id.isdigit():
            raise ValueError(f"Invalid composite_item_id '{composite_item_id}'. Expected real numeric Zoho Composite Item ID.")

        org_id = organization_id or self.token_manager.organization_id
        token = self.token_manager.get_valid_access_token()
        if not token:
            raise RuntimeError("No valid Zoho Books access token available.")

        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/compositeitems/{clean_id}"
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        params = {"organization_id": org_id}

        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code == 401 and self.token_manager._refresh_token:
                self.token_manager.refresh_access_token()
                token = self.token_manager.get_valid_access_token()
                headers["Authorization"] = f"Zoho-oauthtoken {token}"
                resp = client.get(url, headers=headers, params=params)

            if resp.status_code == 404:
                raise ValueError(f"Composite item '{clean_id}' not found in Zoho Books (404).")
            if resp.status_code == 401:
                raise RuntimeError("Zoho Books authentication failure (401). Check OAuth scopes.")
            if resp.status_code == 403:
                raise RuntimeError("Zoho Books permission denied (403).")
            if resp.status_code != 200:
                raise RuntimeError(f"Zoho Books API error (HTTP {resp.status_code}): {resp.text[:200]}")

            return resp.json()

    def create_composite_item(
        self,
        payload: dict[str, Any],
        organization_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Creates a new composite item in Zoho Books:
        POST https://www.zohoapis.com/books/v3/compositeitems?organization_id={org_id}

        Payload requirements:
        - name: str (required)
        - mapped_items: list of constituent items with real numeric item_id and quantity > 0
        """
        if not payload or not isinstance(payload, dict):
            raise ValueError("Payload must be a non-empty dictionary.")

        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Composite item 'name' is required.")

        mapped_items = payload.get("mapped_items")
        if not mapped_items or not isinstance(mapped_items, list) or len(mapped_items) == 0:
            raise ValueError("Composite item requires at least one constituent item in 'mapped_items'.")

        # Validate that all component item_ids are real numeric IDs
        for idx, comp in enumerate(mapped_items):
            raw_comp_id = str(comp.get("item_id") or "").strip()
            if not raw_comp_id or not raw_comp_id.isdigit() or raw_comp_id.startswith("ZB-NEW-"):
                raise ValueError(
                    f"Component [{idx}] has invalid item_id '{raw_comp_id}'. "
                    f"All component item IDs must be real numeric Zoho item IDs."
                )
            qty = comp.get("quantity")
            if qty is None or float(qty) <= 0:
                raise ValueError(f"Component [{idx}] ({raw_comp_id}) must have quantity > 0.")

        org_id = organization_id or self.token_manager.organization_id
        token = self.token_manager.get_valid_access_token()
        if not token:
            raise RuntimeError("Zoho Books authentication failure: No valid access token available.")

        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/compositeitems"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }
        params = {"organization_id": org_id}

        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, headers=headers, params=params, json=payload)
            if resp.status_code == 401 and self.token_manager._refresh_token:
                ref_res = self.token_manager.refresh_access_token()
                if ref_res.get("success"):
                    token = self.token_manager.get_valid_access_token()
                    headers["Authorization"] = f"Zoho-oauthtoken {token}"
                    resp = client.post(url, headers=headers, params=params, json=payload)

            resp_json: dict[str, Any] = {}
            try:
                resp_json = resp.json()
            except Exception:
                pass

            if resp.status_code == 401:
                raise RuntimeError("Zoho Books authentication failure (401). Check OAuth scopes.")
            if resp.status_code == 403:
                raise RuntimeError("Zoho Books permission denied (403).")
            if resp.status_code not in (200, 201) or resp_json.get("code") != 0:
                err_msg = resp_json.get("message") or f"HTTP {resp.status_code}"
                raise RuntimeError(f"Zoho Books composite item creation failed: {err_msg}")

            composite_item = resp_json.get("composite_item") or {}
            raw_created_id = str(
                composite_item.get("composite_item_id")
                or composite_item.get("item_id")
                or resp_json.get("composite_item_id")
                or ""
            ).strip()

            if not raw_created_id or not raw_created_id.isdigit() or raw_created_id.startswith("ZB-NEW-"):
                raise ValueError(
                    f"Zoho Books returned invalid or non-numeric composite_item_id: '{raw_created_id}'"
                )

            return {
                "success": True,
                "composite_item_id": raw_created_id,
                "message": resp_json.get("message") or "Composite item created successfully",
                "composite_item": composite_item,
            }

    def update_composite_item(
        self,
        composite_item_id: str,
        payload: dict[str, Any],
        organization_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Updates an existing composite item in Zoho Books:
        PUT https://www.zohoapis.com/books/v3/compositeitems/{composite_item_id}?organization_id={org_id}

        Safety requirements:
        - composite_item_id must be real numeric Zoho ID
        - Rejects fake IDs, empty IDs, non-numeric IDs
        - Caller cannot replace composite_item_id inside payload
        """
        clean_id = str(composite_item_id or "").strip()
        if not clean_id or not clean_id.isdigit() or clean_id.startswith("ZB-NEW-"):
            raise ValueError(f"Invalid composite_item_id '{composite_item_id}'. Expected real numeric Zoho Composite Item ID.")

        if not payload or not isinstance(payload, dict):
            raise ValueError("Payload must be a non-empty dictionary.")

        # Prevent caller from replacing ID inside payload
        clean_payload = dict(payload)
        clean_payload.pop("composite_item_id", None)
        clean_payload.pop("item_id", None)

        # If mapped_items is present in update, validate component IDs
        if "mapped_items" in clean_payload:
            mapped_items = clean_payload["mapped_items"]
            if not isinstance(mapped_items, list) or len(mapped_items) == 0:
                raise ValueError("Update 'mapped_items' must be a non-empty list.")
            for idx, comp in enumerate(mapped_items):
                raw_comp_id = str(comp.get("item_id") or "").strip()
                if not raw_comp_id or not raw_comp_id.isdigit() or raw_comp_id.startswith("ZB-NEW-"):
                    raise ValueError(
                        f"Component [{idx}] has invalid item_id '{raw_comp_id}'. "
                        f"All component item IDs must be real numeric Zoho item IDs."
                    )

        org_id = organization_id or self.token_manager.organization_id
        token = self.token_manager.get_valid_access_token()
        if not token:
            raise RuntimeError("Zoho Books authentication failure: No valid access token available.")

        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/compositeitems/{clean_id}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }
        params = {"organization_id": org_id}

        with httpx.Client(timeout=25.0) as client:
            resp = client.put(url, headers=headers, params=params, json=clean_payload)
            if resp.status_code == 401 and self.token_manager._refresh_token:
                ref_res = self.token_manager.refresh_access_token()
                if ref_res.get("success"):
                    token = self.token_manager.get_valid_access_token()
                    headers["Authorization"] = f"Zoho-oauthtoken {token}"
                    resp = client.put(url, headers=headers, params=params, json=clean_payload)

            resp_json: dict[str, Any] = {}
            try:
                resp_json = resp.json()
            except Exception:
                pass

            if resp.status_code == 404:
                raise ValueError(f"Composite item '{clean_id}' not found in Zoho Books (404).")
            if resp.status_code == 401:
                raise RuntimeError("Zoho Books authentication failure (401). Check OAuth scopes.")
            if resp.status_code == 403:
                raise RuntimeError("Zoho Books permission denied (403).")
            if resp.status_code not in (200, 201) or resp_json.get("code") != 0:
                err_msg = resp_json.get("message") or f"HTTP {resp.status_code}"
                raise RuntimeError(f"Zoho Books composite item update failed: {err_msg}")

            composite_item = resp_json.get("composite_item") or {}
            return {
                "success": True,
                "composite_item_id": clean_id,
                "message": resp_json.get("message") or "Composite item updated successfully",
                "composite_item": composite_item,
            }

    def find_composite_item_by_exact_sku(
        self,
        sku: str,
        organization_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Searches the REAL Zoho Books API for an exact composite item SKU / Part Number match.
        Target:
        GET https://www.zohoapis.com/books/v3/compositeitems?organization_id={org_id}&search_text={sku}

        Strict Matching Rules:
        1. Queries real Zoho Books API; never uses mock catalog or fixture data.
        2. Exact SKU / Part Number match:
           - Matches item.sku or item.part_number (case-insensitive strip).
           - Description-only or Name-only match does NOT qualify as a match.
        3. Validates that matched item has a real numeric composite_item_id.
        4. Returns the matched item dictionary if found with valid numeric ID.
        5. Returns None if NOT FOUND, if SKU is blank, or on any error.
        """
        target_sku = (sku or "").strip()
        if not target_sku:
            return None

        org_id = organization_id or self.token_manager.organization_id
        res = self.list_composite_items(organization_id=org_id, search_text=target_sku)
        if not res.get("success"):
            return None

        items = res.get("composite_items", [])
        for item in items:
            item_sku = (item.get("sku") or "").strip()
            item_part = (item.get("part_number") or "").strip()

            is_exact_sku_match = (
                (item_sku and item_sku.lower() == target_sku.lower()) or
                (item_part and item_part.lower() == target_sku.lower())
            )

            if is_exact_sku_match:
                raw_id = str(item.get("composite_item_id") or item.get("item_id") or "").strip()
                if raw_id.isdigit() and not raw_id.startswith("ZB-NEW-"):
                    return item
                else:
                    logger.warning(f"Composite item matched SKU '{target_sku}' but has non-numeric ID: '{raw_id}'")

        return None


    def find_item_by_exact_sku(
        self,
        sku: str,
        organization_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Searches the REAL Zoho Books API for an exact SKU / Part Number match.
        Target:
        GET https://www.zohoapis.com/books/v3/items?organization_id={org_id}&search_text={sku}

        Strict Matching Rules:
        1. MUST query the real Zoho Books API; NEVER uses mock data, local catalog, or fixture data.
        2. Exact SKU / Part Number match in REAL Zoho Books:
           - Matches item.sku or item.part_number (case-insensitive strip).
           - Description-only match does NOT qualify as a match.
        3. Validates that matched item has a real numeric item_id.
        4. Returns the matched item dictionary if found with valid numeric item_id.
        5. Returns None if NOT FOUND, if SKU is blank, or on any error (caller classifies as CREATE).
        """
        target_sku = (sku or "").strip()
        if not target_sku:
            return None

        org_id = organization_id or self.token_manager.organization_id
        token = self.token_manager.get_valid_access_token()
        if not token:
            if self.token_manager.grant_token and self.token_manager.is_configured():
                ex_res = self.token_manager.exchange_grant_token()
                if ex_res.get("success"):
                    token = self.token_manager.get_valid_access_token()

        if not token:
            logger.warning(f"No Zoho Books access token available for exact SKU lookup of '{target_sku}'.")
            return None

        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/items"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
        }
        params = {
            "organization_id": org_id,
            "search_text": target_sku,
        }

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code == 401 and self.token_manager._refresh_token:
                    ref_res = self.token_manager.refresh_access_token()
                    if ref_res.get("success"):
                        token = self.token_manager.get_valid_access_token()
                        headers["Authorization"] = f"Zoho-oauthtoken {token}"
                        resp = client.get(url, headers=headers, params=params)

                if resp.status_code != 200:
                    logger.warning(f"Zoho Books exact SKU search failed with HTTP {resp.status_code} for SKU '{target_sku}'")
                    return None

                data = resp.json()
                items = data.get("items", [])

                for item in items:
                    item_sku = (item.get("sku") or "").strip()
                    item_part = (item.get("part_number") or "").strip()

                    # Exact SKU / Part Number equality check (case-insensitive)
                    is_exact_sku_match = (
                        (item_sku and item_sku.lower() == target_sku.lower()) or
                        (item_part and item_part.lower() == target_sku.lower())
                    )

                    if is_exact_sku_match:
                        raw_id = str(item.get("item_id") or "").strip()
                        if raw_id.isdigit():
                            return item
                        else:
                            logger.warning(f"Item matched SKU '{target_sku}' but has non-numeric item_id: '{raw_id}'")

                # No exact SKU match among returned items
                return None
        except Exception as e:
            logger.error(f"Zoho Books API error during exact SKU lookup for '{target_sku}': {e}")
            return None

    def test_connectivity(self, organization_id: Optional[str] = None) -> dict[str, Any]:
        """
        Executes read-only Zoho Books connectivity test.
        Target:
        GET https://www.zohoapis.com/books/v3/items
        organization_id = 741367552
        search_text = TEST-AUTOMATION-001

        Expected:
        SKU = TEST-AUTOMATION-001
        Item ID = 2552396000020372001
        """
        org_id = organization_id or self.token_manager.organization_id
        search_res = self.search_items(
            search_text=TEST_AUTOMATION_SKU,
            organization_id=org_id,
        )

        matched_item = None
        for it in search_res.get("items", []):
            if (it.get("sku") == TEST_AUTOMATION_SKU or it.get("part_number") == TEST_AUTOMATION_SKU) and str(it.get("item_id")) == TEST_AUTOMATION_ITEM_ID:
                matched_item = it
                break

        is_match = matched_item is not None
        status_summary = self.token_manager.get_status_summary()

        return {
            "success": is_match,
            "organization_id": org_id,
            "tested_sku": TEST_AUTOMATION_SKU,
            "expected_item_id": TEST_AUTOMATION_ITEM_ID,
            "matched_item_id": matched_item.get("item_id") if matched_item else None,
            "is_match": is_match,
            "item_name": matched_item.get("name") if matched_item else None,
            "rate": matched_item.get("rate") if matched_item else None,
            "source": search_res.get("source"),
            "connection_status": status_summary,
            "message": (
                f"Zoho Books connectivity verified: SKU '{TEST_AUTOMATION_SKU}' matches Item ID '{TEST_AUTOMATION_ITEM_ID}'."
                if is_match
                else f"Zoho Books search for '{TEST_AUTOMATION_SKU}' did not return expected Item ID '{TEST_AUTOMATION_ITEM_ID}'."
            ),
        }

    def strict_live_connectivity_test(
        self,
        organization_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        STRICT LIVE Zoho Books connectivity verification.
        MUST NOT use mock data, local catalog, or fallback test records.
        MUST obtain real OAuth access token and make real HTTPS request to:
        GET https://www.zohoapis.com/books/v3/items
        with organization_id=741367552 & search_text=TEST-AUTOMATION-001
        """
        org_id = organization_id or self.token_manager.organization_id

        # 1. Obtain real access token
        token = self.token_manager.get_valid_access_token()
        if not token:
            if self.token_manager.grant_token and self.token_manager.is_configured():
                ex_res = self.token_manager.exchange_grant_token()
                if ex_res.get("success"):
                    token = self.token_manager.get_valid_access_token()

        if not token:
            return {
                "success": False,
                "real_zoho_api_request": "FAIL",
                "real_oauth_token": "FAIL",
                "real_sku_search": "FAIL",
                "fallback_mock_used": "NO",
                "organization_id": org_id,
                "error": "Failed to obtain real Zoho OAuth access token. Ensure client_id, client_secret, and grant_token (or refresh_token) are valid.",
            }

        # 2. Make real HTTPS request to Zoho Books API
        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/items"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
        }
        params = {
            "organization_id": org_id,
            "search_text": TEST_AUTOMATION_SKU,
        }

        try:
            with httpx.Client(timeout=25.0) as client:
                resp = client.get(url, headers=headers, params=params)

                # Handle token expiry retry once
                if resp.status_code == 401 and self.token_manager._refresh_token:
                    ref_res = self.token_manager.refresh_access_token()
                    if ref_res.get("success"):
                        token = self.token_manager.get_valid_access_token()
                        headers["Authorization"] = f"Zoho-oauthtoken {token}"
                        resp = client.get(url, headers=headers, params=params)

                resp_json = {}
                try:
                    resp_json = resp.json()
                except Exception:
                    pass

                http_status = resp.status_code
                zoho_code = resp_json.get("code")
                zoho_message = resp_json.get("message")
                items = resp_json.get("items", [])

                if http_status != 200:
                    return {
                        "success": False,
                        "real_zoho_api_request": "FAIL",
                        "real_oauth_token": "PASS",
                        "real_sku_search": "FAIL",
                        "fallback_mock_used": "NO",
                        "http_status": http_status,
                        "zoho_code": zoho_code,
                        "zoho_message": zoho_message,
                        "organization_id": org_id,
                    }

                # 3. Find matching SKU and Item ID from real response
                matched_item = None
                for it in items:
                    sku_val = it.get("sku") or it.get("part_number") or ""
                    if sku_val == TEST_AUTOMATION_SKU or str(it.get("item_id")) == TEST_AUTOMATION_ITEM_ID:
                        matched_item = it
                        break

                is_match = bool(matched_item and str(matched_item.get("item_id")) == TEST_AUTOMATION_ITEM_ID)
                matched_sku = matched_item.get("sku") if matched_item else (items[0].get("sku") if items else None)
                matched_item_id = str(matched_item.get("item_id")) if matched_item else (str(items[0].get("item_id")) if items else None)

                return {
                    "success": is_match,
                    "real_zoho_api_request": "PASS",
                    "real_oauth_token": "PASS",
                    "real_sku_search": "PASS" if is_match else "FAIL",
                    "fallback_mock_used": "NO",
                    "http_status": http_status,
                    "zoho_code": zoho_code,
                    "zoho_message": zoho_message,
                    "organization_id": org_id,
                    "tested_sku": TEST_AUTOMATION_SKU,
                    "matched_sku": matched_sku,
                    "expected_item_id": TEST_AUTOMATION_ITEM_ID,
                    "matched_item_id": matched_item_id,
                    "items_returned_count": len(items),
                    "token_expiry_status": {
                        "expires_in_seconds": max(0, int(self.token_manager._expires_at - time.time())),
                        "has_refresh_token": bool(self.token_manager._refresh_token),
                    },
                }

        except Exception as e:
            return {
                "success": False,
                "real_zoho_api_request": "FAIL",
                "real_oauth_token": "PASS",
                "real_sku_search": "FAIL",
                "fallback_mock_used": "NO",
                "organization_id": org_id,
                "error": f"Live HTTPS request to Zoho Books failed: {str(e)}",
            }

    def get_item(self, item_id: str, organization_id: Optional[str] = None) -> dict[str, Any]:
        """Fetches a single item from Zoho Books: GET /books/v3/items/{item_id}?organization_id={org_id}."""
        org_id = organization_id or self.token_manager.organization_id
        token = self.token_manager.get_valid_access_token()
        if not token:
            raise RuntimeError("No valid Zoho Books access token available.")

        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/items/{item_id}"
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        params = {"organization_id": org_id}

        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code == 401 and self.token_manager._refresh_token:
                self.token_manager.refresh_access_token()
                token = self.token_manager.get_valid_access_token()
                headers["Authorization"] = f"Zoho-oauthtoken {token}"
                resp = client.get(url, headers=headers, params=params)
            return resp.json()

    def create_item(self, payload: dict[str, Any], organization_id: Optional[str] = None) -> dict[str, Any]:
        """Creates a new item in Zoho Books: POST /books/v3/items?organization_id={org_id}."""
        org_id = organization_id or self.token_manager.organization_id
        token = self.token_manager.get_valid_access_token()
        if not token:
            raise RuntimeError("No valid Zoho Books access token available.")

        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/items"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }
        params = {"organization_id": org_id}

        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, headers=headers, params=params, json=payload)
            if resp.status_code == 401 and self.token_manager._refresh_token:
                self.token_manager.refresh_access_token()
                token = self.token_manager.get_valid_access_token()
                headers["Authorization"] = f"Zoho-oauthtoken {token}"
                resp = client.post(url, headers=headers, params=params, json=payload)
            return resp.json()

    def update_item(self, item_id: str, payload: dict[str, Any], organization_id: Optional[str] = None) -> dict[str, Any]:
        """Updates an item in Zoho Books: PUT /books/v3/items/{item_id}?organization_id={org_id}."""
        clean_id = str(item_id).strip()
        if not clean_id.isdigit():
            raise ValueError(f"Invalid Zoho Books item_id '{item_id}'. Expected numeric Zoho Item ID.")

        org_id = organization_id or self.token_manager.organization_id
        token = self.token_manager.get_valid_access_token()
        if not token:
            raise RuntimeError("No valid Zoho Books access token available.")

        api_base = self.token_manager.get_effective_api_domain().rstrip("/")
        url = f"{api_base}/books/v3/items/{item_id}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }
        params = {"organization_id": org_id}

        with httpx.Client(timeout=20.0) as client:
            resp = client.put(url, headers=headers, params=params, json=payload)
            if resp.status_code == 401 and self.token_manager._refresh_token:
                self.token_manager.refresh_access_token()
                token = self.token_manager.get_valid_access_token()
                headers["Authorization"] = f"Zoho-oauthtoken {token}"
                resp = client.put(url, headers=headers, params=params, json=payload)
            return resp.json()

    def controlled_update_test(
        self,
        item_id: str = TEST_AUTOMATION_ITEM_ID,
        sku: str = TEST_AUTOMATION_SKU,
        new_description: str = "QuotexAI UPDATE TEST - 16 Sep 2026",
    ) -> dict[str, Any]:
        """
        Executes controlled real Zoho Books write test on TEST-AUTOMATION-001.
        1. GET current item details.
        2. PUT updated description through official update_item method.
        3. GET item again and verify description changed while preserving all other fields.
        """
        org_id = self.token_manager.organization_id

        # 1. GET item before update
        before_resp = self.get_item(item_id, org_id)
        if before_resp.get("code") != 0:
            return {
                "update_api": "FAIL",
                "post_update_verification": "FAIL",
                "sku_preserved": "FAIL",
                "item_id_preserved": "FAIL",
                "unintended_changes": "YES",
                "error": f"Initial GET failed: {before_resp.get('message')}",
            }

        before_item = before_resp.get("item", {})
        before_name = before_item.get("name")
        before_rate = before_item.get("rate")
        before_sku = before_item.get("sku")
        before_unit = before_item.get("unit")
        before_product_type = before_item.get("product_type")

        # 2. PUT updated description preserving name and rate
        update_payload = {
            "name": before_name,
            "rate": before_rate,
            "description": new_description,
        }
        put_resp = self.update_item(item_id, update_payload, org_id)
        put_success = (put_resp.get("code") == 0)

        if not put_success:
            return {
                "update_api": "FAIL",
                "post_update_verification": "FAIL",
                "sku_preserved": "FAIL",
                "item_id_preserved": "FAIL",
                "unintended_changes": "YES",
                "error": f"PUT failed: {put_resp.get('message')}",
            }

        # 3. GET item after update for strict verification
        after_resp = self.get_item(item_id, org_id)
        if after_resp.get("code") != 0:
            return {
                "update_api": "PASS",
                "post_update_verification": "FAIL",
                "sku_preserved": "FAIL",
                "item_id_preserved": "FAIL",
                "unintended_changes": "YES",
                "error": f"Post-update GET failed: {after_resp.get('message')}",
            }

        after_item = after_resp.get("item", {})
        after_desc = after_item.get("description")
        after_sku = after_item.get("sku")
        after_id = str(after_item.get("item_id"))
        after_name = after_item.get("name")
        after_rate = after_item.get("rate")
        after_unit = after_item.get("unit")
        after_product_type = after_item.get("product_type")

        # 4. Strict assertions
        desc_matches = (after_desc == new_description)
        sku_preserved = (after_sku == sku and after_sku == before_sku)
        item_id_preserved = (after_id == item_id)
        other_fields_preserved = (
            after_name == before_name
            and after_rate == before_rate
            and after_unit == before_unit
            and after_product_type == before_product_type
        )
        unintended_changes = not other_fields_preserved

        return {
            "update_api": "PASS" if put_success else "FAIL",
            "post_update_verification": "PASS" if desc_matches else "FAIL",
            "sku_preserved": "PASS" if sku_preserved else "FAIL",
            "item_id_preserved": "PASS" if item_id_preserved else "FAIL",
            "unintended_changes": "NO" if not unintended_changes else "YES",
        }


zoho_books_service = ZohoBooksService()
