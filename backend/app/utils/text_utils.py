import re
from typing import Optional, Any, Tuple

# Comprehensive currency symbols mapping
CURRENCY_SYMBOLS: dict[str, str] = {
    "EUR": "€",
    "USD": "$",
    "INR": "₹",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "IDR": "Rp",
    "SGD": "S$",
    "AUD": "A$",
    "CAD": "C$",
    "CHF": "CHF",
    "AED": "AED",
}

SYMBOL_TO_CURRENCY: dict[str, str] = {
    "€": "EUR",
    "\u20ac": "EUR",
    "$": "USD",
    "₹": "INR",
    "rs": "INR",
    "inr": "INR",
    "£": "GBP",
    "¥": "JPY",
    "rp": "IDR",
    "idr": "IDR",
    "s$": "SGD",
    "sgd": "SGD",
}


def normalize_price(price_str: Any) -> Optional[float]:
    """Parses various price formats ($1,234.56, 1.234,56 €, € 562.00, \ufffd 1,240.59, 85,000.00, etc.) to float."""
    if price_str is None:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    
    cleaned = str(price_str).strip()
    # Remove unicode replacement char or currency symbols
    cleaned = re.sub(r'[\ufffd€$£₹¥\s]', '', cleaned)
    # Remove currency words if attached
    cleaned = re.sub(r'(?i)\b(eur|usd|inr|gbp|idr|jpy|cny|sgd|rs|rp)\b', '', cleaned).strip()
    # Remove non-numeric except dot, comma, minus
    cleaned = re.sub(r'[^\d.,\-]', '', cleaned)
    if not cleaned or cleaned in ('-', '.', ','):
        return None
    
    # Handle European decimal: e.g. 1.234,56 -> 1234.56 or 562,00 -> 562.00
    if ',' in cleaned and '.' in cleaned:
        if cleaned.rfind(',') > cleaned.rfind('.'):
            # 1.234,56 format
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # 1,234.56 format (e.g. 1,240.59 -> 1240.59)
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            cleaned = f"{parts[0]}.{parts[1]}"
        else:
            # 85,000 without decimals -> 85000
            cleaned = cleaned.replace(',', '')
            
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_currency(text: str) -> str:
    """Detects currency symbol or code from quotation text.
    Priority:
    1. Direct price symbol (€, $, ₹, £, ¥, Rp)
    2. Explicit ISO code (EUR, USD, INR, GBP, IDR, JPY, CNY)
    3. Country / Context evidence
    Default: EUR if ambiguous.
    """
    if not text:
        return "EUR"
    
    # 1. Check explicit currency symbols
    if "€" in text or "\u20ac" in text:
        return "EUR"
    if "₹" in text:
        return "INR"
    if "£" in text or "\u00a3" in text:
        return "GBP"
    if "¥" in text or "\u00a5" in text:
        # Contextual check: Japan vs China
        if "china" in text.lower() or "cny" in text.lower() or "rmb" in text.lower():
            return "CNY"
        return "JPY"
    if "rp" in text.lower() or "idr" in text.lower() or "indonesia" in text.lower() and "idr" in text.lower():
        return "IDR"
    if "$" in text or "usd" in text.lower():
        if "s$" in text.lower() or "sgd" in text.lower() or "singapore" in text.lower():
            return "SGD"
        if "a$" in text.lower() or "aud" in text.lower() or "australia" in text.lower():
            return "AUD"
        if "c$" in text.lower() or "cad" in text.lower() or "canada" in text.lower():
            return "CAD"
        return "USD"

    # 2. Check explicit text codes
    text_upper = text.upper()
    for code in ["EUR", "USD", "INR", "GBP", "JPY", "CNY", "IDR", "SGD", "AED", "AUD", "CAD", "CHF"]:
        # Word boundary match for ISO codes
        if re.search(rf'\b{code}\b', text_upper):
            return code
            
    if re.search(r'\b(?:RS|RUPEES|INR)\b', text_upper):
        return "INR"

    return "EUR"


def get_currency_symbol(currency_code: str) -> str:
    """Returns currency symbol corresponding to currency code."""
    return CURRENCY_SYMBOLS.get(currency_code.upper(), currency_code)


def clean_part_number(raw_pn: Any) -> str:
    """Strictly extracts and cleans part number as string, keeping leading zeros."""
    if raw_pn is None:
        return ""
    pn_str = str(raw_pn).strip()
    pn_str = re.sub(r'^["\']|["\']$', '', pn_str)
    return pn_str

