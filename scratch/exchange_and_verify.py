import sys
import json
import time
import httpx
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
SELF_CLIENT_PATH = ROOT_DIR / "self_client.json"
TOKEN_CACHE_PATH = ROOT_DIR / "zoho_tokens.json"

def main():
    if not SELF_CLIENT_PATH.exists():
        print(json.dumps({"error": "self_client.json not found"}))
        sys.exit(1)

    with open(SELF_CLIENT_PATH, "r", encoding="utf-8") as f:
        sc = json.load(f)

    client_id = sc.get("client_id")
    client_secret = sc.get("client_secret")
    code = sc.get("code")
    scopes = sc.get("scope", [])

    if not client_id or not client_secret or not code:
        print(json.dumps({"error": "Missing client credentials or code"}))
        sys.exit(1)

    print("Step 1: Exchanging authorization code for tokens...")
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(token_url, data=data)
        token_data = resp.json()

    if "error" in token_data:
        print(json.dumps({
            "step": "exchange",
            "status": "FAILED",
            "error": token_data.get("error")
        }))
        sys.exit(1)

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    api_domain = token_data.get("api_domain", "https://www.zohoapis.com")

    if not access_token:
        print(json.dumps({"step": "exchange", "status": "FAILED", "error": "No access token in response"}))
        sys.exit(1)

    # Save to zoho_tokens.json
    cache_payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": time.time() + float(expires_in),
        "api_domain": api_domain,
        "updated_at": time.time(),
        "scopes": scopes
    }
    with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache_payload, f, indent=2)

    print("Step 1 SUCCESS: New tokens cached to zoho_tokens.json.")
    print(f"Configured Scopes: {len(scopes)} scopes ({', '.join(scopes)})")

    # Step 2: Test READ on normal items
    print("Step 2: Testing READ on /books/v3/items...")
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }
    org_id = "741367552"

    with httpx.Client(timeout=20.0) as client:
        read_resp = client.get(
            f"{api_domain.rstrip('/')}/books/v3/items",
            headers=headers,
            params={"organization_id": org_id, "per_page": 5}
        )
        read_status = read_resp.status_code
        try:
            read_json = read_resp.json()
            read_code = read_json.get("code")
            read_msg = read_json.get("message")
            item_count = len(read_json.get("items", []))
        except Exception as e:
            read_code = -1
            read_msg = str(e)
            item_count = 0

    print(f"READ Items Result -> HTTP: {read_status}, Zoho Code: {read_code}, Msg: {read_msg}, Count: {item_count}")

    # Step 3: Test controlled CREATE on normal item
    # Note: Using unique timestamp in SKU to ensure isolation and NOT touching any production quotation item
    print("Step 3: Testing controlled CREATE for a permission verification test item...")
    test_sku = f"TEST-AUTH-PERM-{int(time.time())}"
    test_payload = {
        "name": f"QuotexAI Permission Check ({test_sku})",
        "rate": 1000.0,
        "sku": test_sku,
        "description": "Temporary test item to verify Zoho Books item CREATE permission."
    }

    created_item_id = None
    with httpx.Client(timeout=20.0) as client:
        create_resp = client.post(
            f"{api_domain.rstrip('/')}/books/v3/items",
            headers=headers,
            params={"organization_id": org_id},
            json=test_payload
        )
        create_status = create_resp.status_code
        try:
            create_json = create_resp.json()
            create_code = create_json.get("code")
            create_msg = create_json.get("message")
            created_item = create_json.get("item", {})
            created_item_id = created_item.get("item_id")
        except Exception as e:
            create_code = -1
            create_msg = str(e)

    print(f"CREATE Item Result -> HTTP: {create_status}, Zoho Code: {create_code}, Msg: {create_msg}, Created Item ID: {created_item_id}")

    # Clean up test item if created
    if created_item_id and create_status in (200, 201) and create_code == 0:
        print(f"Cleaning up verification test item {created_item_id}...")
        with httpx.Client(timeout=20.0) as client:
            del_resp = client.delete(
                f"{api_domain.rstrip('/')}/books/v3/items/{created_item_id}",
                headers=headers,
                params={"organization_id": org_id}
            )
            print(f"DELETE Test Item Result -> HTTP: {del_resp.status_code}, Zoho Code: {del_resp.json().get('code') if del_resp.headers.get('content-type', '').startswith('application/json') else 'N/A'}")

    # Step 4: Test Composite Item READ only
    print("Step 4: Testing Composite Item READ on /books/v3/compositeitems...")
    with httpx.Client(timeout=20.0) as client:
        comp_resp = client.get(
            f"{api_domain.rstrip('/')}/books/v3/compositeitems",
            headers=headers,
            params={"organization_id": org_id, "per_page": 5}
        )
        comp_status = comp_resp.status_code
        try:
            comp_json = comp_resp.json()
            comp_code = comp_json.get("code")
            comp_msg = comp_json.get("message")
            comp_count = len(comp_json.get("composite_items", []))
        except Exception as e:
            comp_code = -1
            comp_msg = str(e)
            comp_count = 0

    print(f"Composite Items READ Result -> HTTP: {comp_status}, Zoho Code: {comp_code}, Msg: {comp_msg}, Count: {comp_count}")

if __name__ == "__main__":
    main()
