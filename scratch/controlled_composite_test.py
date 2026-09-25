import json
import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.services.zoho_books_service import zoho_books_service

def run_test():
    report = {}

    # STEP 1: Verify OAuth Permissions
    print("=== STEP 1: VERIFY OAUTH PERMISSIONS ===")
    token_mgr = zoho_books_service.token_manager
    cached_tokens_path = BASE_DIR / "zoho_tokens.json"
    
    with open(cached_tokens_path, "r", encoding="utf-8") as f:
        token_data = json.load(f)

    active_scopes = token_data.get("scopes", [])
    report["configured_scopes"] = active_scopes

    required_composite_scopes = [
        "ZohoBooks.compositeitems.READ",
        "ZohoBooks.compositeitems.CREATE",
        "ZohoBooks.compositeitems.UPDATE",
    ]
    required_normal_scopes = [
        "ZohoBooks.items.READ",
        "ZohoBooks.items.CREATE",
        "ZohoBooks.items.UPDATE",
    ]

    missing_composite = [s for s in required_composite_scopes if s not in active_scopes]
    missing_normal = [s for s in required_normal_scopes if s not in active_scopes]

    if missing_composite or missing_normal:
        print(f"STOP: Missing required scopes. Composite: {missing_composite}, Normal: {missing_normal}")
        report["step1_status"] = "FAILED"
        report["missing_scopes"] = missing_composite + missing_normal
        print(json.dumps(report, indent=2))
        return

    # Verify active access token
    token = token_mgr.get_valid_access_token()
    if not token:
        print("STOP: No valid access token available.")
        report["step1_status"] = "FAILED"
        print(json.dumps(report, indent=2))
        return

    report["step1_status"] = "SUCCESS"
    report["oauth"] = {
        "composite_read": "ZohoBooks.compositeitems.READ" in active_scopes,
        "composite_create": "ZohoBooks.compositeitems.CREATE" in active_scopes,
        "composite_update": "ZohoBooks.compositeitems.UPDATE" in active_scopes,
        "items_read": "ZohoBooks.items.READ" in active_scopes,
        "items_create": "ZohoBooks.items.CREATE" in active_scopes,
        "items_update": "ZohoBooks.items.UPDATE" in active_scopes,
    }
    print("STEP 1 SUCCESS: All required scopes are present.")

    # STEP 2: Verify Real Test Components
    print("\n=== STEP 2: VERIFY REAL TEST COMPONENTS ===")
    comp1_id = "2552396000020372001"
    comp2_id = "2552396000020392002"

    print(f"Checking component 1: {comp1_id}...")
    c1_res = zoho_books_service.get_item(comp1_id)
    c1_item = c1_res.get("item")
    if not c1_item or c1_res.get("code") != 0:
        print(f"STOP: Component 1 ({comp1_id}) does not exist in Zoho Books. Response: {c1_res}")
        report["step2_status"] = "FAILED"
        report["missing_component"] = comp1_id
        print(json.dumps(report, indent=2))
        return
    c1_name = c1_item.get("name")
    c1_sku = c1_item.get("sku") or c1_item.get("part_number") or ""
    print(f"Component 1 verified: Name='{c1_name}', SKU='{c1_sku}'")

    print(f"Checking component 2: {comp2_id}...")
    c2_res = zoho_books_service.get_item(comp2_id)
    c2_item = c2_res.get("item")
    if not c2_item or c2_res.get("code") != 0:
        print(f"STOP: Component 2 ({comp2_id}) does not exist in Zoho Books. Response: {c2_res}")
        report["step2_status"] = "FAILED"
        report["missing_component"] = comp2_id
        print(json.dumps(report, indent=2))
        return
    c2_name = c2_item.get("name")
    c2_sku = c2_item.get("sku") or c2_item.get("part_number") or ""
    print(f"Component 2 verified: Name='{c2_name}', SKU='{c2_sku}'")

    report["step2_status"] = "SUCCESS"
    report["components"] = {
        "component_1": {"id": comp1_id, "name": c1_name, "sku": c1_sku, "exists": True},
        "component_2": {"id": comp2_id, "name": c2_name, "sku": c2_sku, "exists": True},
    }

    # STEP 3: Create ONE Test Composite Item
    print("\n=== STEP 3: CREATE ONE TEST COMPOSITE ITEM ===")
    
    # Check if SKU already exists
    existing_match = zoho_books_service.find_composite_item_by_exact_sku("TEST-COMPOSITE-001")
    if existing_match:
        print(f"Notice: Composite item with SKU TEST-COMPOSITE-001 already exists: ID {existing_match.get('composite_item_id')}")
        created_id = str(existing_match.get("composite_item_id") or existing_match.get("item_id"))
        report["step3_status"] = "EXISTED"
        report["created_id"] = created_id
        report["create_result"] = {
            "http_status": 200,
            "zoho_code": 0,
            "composite_id": created_id,
            "sku": "TEST-COMPOSITE-001",
            "name": existing_match.get("name"),
            "rate": existing_match.get("rate"),
        }
    else:
        create_payload = {
            "name": "QuotexAI Composite Test",
            "sku": "TEST-COMPOSITE-001",
            "unit": "Set",
            "description": "Temporary Composite Item created by QuotexAI API integration test",
            "combo_type": "kit",
            "rate": 5000,
            "mapped_items": [
                {
                    "item_id": comp1_id,
                    "quantity": 1
                },
                {
                    "item_id": comp2_id,
                    "quantity": 2
                }
            ]
        }
        print("Sanitized create payload:")
        print(json.dumps(create_payload, indent=2))

        try:
            create_res = zoho_books_service.create_composite_item(create_payload)
            print("Create Response:")
            print(json.dumps({k: v for k, v in create_res.items() if k != "composite_item"}, indent=2))
            created_id = create_res["composite_item_id"]
            report["step3_status"] = "SUCCESS"
            report["created_id"] = created_id
            created_item = create_res.get("composite_item", {})
            report["create_result"] = {
                "http_status": 201,
                "zoho_code": 0,
                "composite_id": created_id,
                "sku": created_item.get("sku", "TEST-COMPOSITE-001"),
                "name": created_item.get("name", "QuotexAI Composite Test"),
                "rate": created_item.get("rate", 5000),
            }
        except Exception as e:
            print(f"STOP: Composite Item creation failed: {e}")
            report["step3_status"] = "FAILED"
            report["create_error"] = str(e)
            print(json.dumps(report, indent=2))
            return

    # STEP 4: Immediate READ Verification
    print(f"\n=== STEP 4: IMMEDIATE READ VERIFICATION ({created_id}) ===")
    get_res = zoho_books_service.get_composite_item(created_id)
    ci = get_res.get("composite_item", {})
    
    ci_id = str(ci.get("composite_item_id") or ci.get("item_id") or "")
    ci_name = ci.get("name")
    ci_sku = ci.get("sku")
    ci_combo = ci.get("combo_type")
    ci_unit = ci.get("unit")
    ci_rate = ci.get("rate")
    ci_status = ci.get("status")
    mapped_items = ci.get("mapped_items", [])

    print(f"Composite ID: {ci_id}")
    print(f"Name: {ci_name}")
    print(f"SKU: {ci_sku}")
    print(f"Combo Type: {ci_combo}")
    print(f"Unit: {ci_unit}")
    print(f"Rate: {ci_rate}")
    print(f"Status: {ci_status}")
    print(f"Components count: {len(mapped_items)}")

    comp_ids = [str(m.get("item_id") or "") for m in mapped_items]
    comp_qtys = [m.get("quantity") for m in mapped_items]
    print(f"Component IDs: {comp_ids}")
    print(f"Component Quantities: {comp_qtys}")

    report["step4_status"] = "SUCCESS" if len(mapped_items) == 2 else "WARNING_COMP_COUNT"
    report["get_verification"] = {
        "composite_id": ci_id,
        "name": ci_name,
        "sku": ci_sku,
        "combo_type": ci_combo,
        "unit": ci_unit,
        "rate": ci_rate,
        "status": ci_status,
        "component_count": len(mapped_items),
        "component_ids": comp_ids,
        "component_quantities": comp_qtys,
    }

    # STEP 5: UPDATE Test
    print(f"\n=== STEP 5: UPDATE TEST ({created_id}) ===")
    update_payload = {
        "name": "QuotexAI Composite Test Updated",
        "description": "Updated by QuotexAI Composite Item integration test",
        "rate": 7500,
        "mapped_items": [
            {
                "item_id": comp1_id,
                "quantity": 1
            },
            {
                "item_id": comp2_id,
                "quantity": 2
            }
        ]
    }
    try:
        update_res = zoho_books_service.update_composite_item(created_id, update_payload)
        print("Update Response:")
        print(json.dumps({k: v for k, v in update_res.items() if k != "composite_item"}, indent=2))
        report["step5_status"] = "SUCCESS"
        report["update_result"] = {
            "http_status": 200,
            "zoho_code": 0,
            "new_name": "QuotexAI Composite Test Updated",
            "new_rate": 7500,
        }
    except Exception as e:
        print(f"STOP: Update failed: {e}")
        report["step5_status"] = "FAILED"
        report["update_error"] = str(e)
        print(json.dumps(report, indent=2))
        return

    # STEP 6: Final GET Verification
    print(f"\n=== STEP 6: FINAL GET VERIFICATION ({created_id}) ===")
    final_get = zoho_books_service.get_composite_item(created_id)
    final_ci = final_get.get("composite_item", {})

    final_name = final_ci.get("name")
    final_sku = final_ci.get("sku")
    final_rate = final_ci.get("rate")
    final_mapped = final_ci.get("mapped_items", [])
    final_comp_ids = [str(m.get("item_id") or "") for m in final_mapped]
    final_comp_qtys = [m.get("quantity") for m in final_mapped]

    print(f"Final Name: {final_name}")
    print(f"Final SKU: {final_sku}")
    print(f"Final Rate: {final_rate}")
    print(f"Final Components count: {len(final_mapped)}")
    print(f"Final Component IDs: {final_comp_ids}")
    print(f"Final Component Quantities: {final_comp_qtys}")

    verified = (
        final_name == "QuotexAI Composite Test Updated" and
        final_sku == "TEST-COMPOSITE-001" and
        float(final_rate) == 7500.0 and
        len(final_mapped) == 2
    )

    report["step6_status"] = "SUCCESS" if verified else "MISMATCH"
    report["final_get"] = {
        "verified": verified,
        "name": final_name,
        "sku": final_sku,
        "rate": final_rate,
        "component_count": len(final_mapped),
        "component_ids": final_comp_ids,
        "component_quantities": final_comp_qtys,
    }

    # STEP 7: Exact SKU Lookup
    print("\n=== STEP 7: EXACT SKU LOOKUP ===")
    sku_match = zoho_books_service.find_composite_item_by_exact_sku("TEST-COMPOSITE-001")
    matched_id = str(sku_match.get("composite_item_id") or sku_match.get("item_id") or "") if sku_match else None
    sku_lookup_verified = (matched_id == created_id)
    print(f"Lookup 'TEST-COMPOSITE-001': Matched ID={matched_id} (Expected={created_id}, Match={sku_lookup_verified})")

    nonexistent_match = zoho_books_service.find_composite_item_by_exact_sku("DOES-NOT-EXIST-COMPOSITE")
    nonexistent_verified = (nonexistent_match is None)
    print(f"Lookup 'DOES-NOT-EXIST-COMPOSITE': Match={nonexistent_match} (Expected=None, Verified={nonexistent_verified})")

    report["step7_status"] = "SUCCESS" if (sku_lookup_verified and nonexistent_verified) else "FAILED"
    report["exact_sku_search"] = {
        "sku_lookup_verified": sku_lookup_verified,
        "matched_id": matched_id,
        "nonexistent_correctly_none": nonexistent_verified,
    }

    # Output full report summary
    print("\n================ FULL TEST SUMMARY ================")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run_test()
