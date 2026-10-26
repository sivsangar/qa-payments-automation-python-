import uuid
from typing import Dict, Optional


def generate_idempotency_key() -> str:
    """Generates a unique UUIDv4 string for payment idempotency headers."""
    return str(uuid.uuid4())


def build_headers(token: str, idempotency_key: Optional[str] = None) -> Dict[str, str]:
    """Constructs standard authentication and idempotency headers."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers