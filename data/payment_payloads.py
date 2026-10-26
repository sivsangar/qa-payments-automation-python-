from typing import Any, Dict


def get_valid_payment_payload(
    amount: float = 250.00,
    currency: str = "CAD",
    source_account: str = "acc_src_1001",
    destination_account: str = "acc_dest_2002",
) -> Dict[str, Any]:
    """Returns a fresh dictionary payload for payment creation."""
    return {
        "amount": amount,
        "currency": currency,
        "source_account": source_account,
        "destination_account": destination_account,
        "description": "Automated QA Payment Lifecycle Test",
    }