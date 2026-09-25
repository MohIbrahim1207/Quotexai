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


MONTH_MAP: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def normalize_price(price_str: Any) -> Optional[float]:
    """Parses various price formats ($1,234.56, 1.234,56 €, € 26.268,00, € 3.317,-, € 1.890, \ufffd 1,240.59, etc.) to float."""
    if price_str is None:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    
    cleaned = str(price_str).strip()
    # Remove unicode replacement char or currency symbols
    cleaned = re.sub(r'[\ufffd€$£₹¥\s]', '', cleaned)
    # Remove currency words if attached
    cleaned = re.sub(r'(?i)\b(eur|usd|inr|gbp|idr|jpy|cny|sgd|rs|rp)\b', '', cleaned).strip()
    # Handle European dash notation: e.g. 3.317,- or 711.- or 3.317,– -> 3.317,00
    cleaned = re.sub(r'[,.][\-–]\s*$', ',00', cleaned)
    # Remove non-numeric except dot, comma, minus
    cleaned = re.sub(r'[^\d.,\-]', '', cleaned)
    if not cleaned or cleaned in ('-', '.', ','):
        return None
    
    # Handle European decimal: e.g. 1.234,56 -> 1234.56 or 562,00 -> 562.00
    if ',' in cleaned and '.' in cleaned:
        if cleaned.rfind(',') > cleaned.rfind('.'):
            # European: 1.234,56 format (e.g. 26.268,00 -> 26268.00)
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US/UK: 1,234.56 format (e.g. 1,240.59 -> 1240.59)
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            cleaned = f"{parts[0]}.{parts[1]}"
        else:
            # 85,000 without decimals -> 85000
            cleaned = cleaned.replace(',', '')
    elif '.' in cleaned:
        # Check if dot is a European thousands separator (e.g. 1.890 or 26.268)
        if re.match(r'^-?\d{1,3}(?:\.\d{3})+$', cleaned):
            cleaned = cleaned.replace('.', '')
            
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_date(date_str: Any) -> Optional[str]:
    """Normalizes dates into ISO YYYY-MM-DD format (e.g. '21 September 2026' -> '2026-09-21')."""
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    # Already YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', cleaned):
        return cleaned
    
    # 21 September 2026 or 21-Sep-2026
    m = re.search(r'(\d{1,2})\s*[-/\s]\s*([A-Za-z]+)\s*[-/\s]\s*(\d{4})', cleaned)
    if m:
        day = int(m.group(1))
        m_str = m.group(2).lower()
        year = int(m.group(3))
        month = MONTH_MAP.get(m_str)
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"
            
    # DD/MM/YYYY or MM/DD/YYYY
    m2 = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})', cleaned)
    if m2:
        p1 = int(m2.group(1))
        p2 = int(m2.group(2))
        yr = int(m2.group(3))
        # Ambiguity check: if p1 > 12, p1 is day
        if p1 > 12:
            return f"{yr:04d}-{p2:02d}-{p1:02d}"
        return f"{yr:04d}-{p1:02d}-{p2:02d}"
        
    return cleaned



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

