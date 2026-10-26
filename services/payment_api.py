from typing import Any, Dict, Optional
from playwright.sync_api import APIRequestContext, APIResponse
from utils.helpers import build_headers, generate_idempotency_key


class PaymentAPI:
    """Service layer encapsulating all Payments API endpoints."""

    def __init__(self, request_context: APIRequestContext, token: str):
        self.request = request_context
        self.token = token

    def create_payment(
        self, payload: Dict[str, Any], idempotency_key: Optional[str] = None
    ) -> APIResponse:
        key = idempotency_key or generate_idempotency_key()
        return self.request.post(
            "/v1/payments",
            data=payload,
            headers=build_headers(self.token, key),
        )

    def authorize_payment(
        self, payment_id: str, idempotency_key: Optional[str] = None
    ) -> APIResponse:
        key = idempotency_key or generate_idempotency_key()
        return self.request.post(
            f"/v1/payments/{payment_id}/authorize",
            headers=build_headers(self.token, key),
        )

    def settle_payment(
        self, payment_id: str, idempotency_key: Optional[str] = None
    ) -> APIResponse:
        key = idempotency_key or generate_idempotency_key()
        return self.request.post(
            f"/v1/payments/{payment_id}/settle",
            headers=build_headers(self.token, key),
        )

    def refund_payment(
        self,
        payment_id: str,
        payload: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> APIResponse:
        key = idempotency_key or generate_idempotency_key()
        return self.request.post(
            f"/v1/payments/{payment_id}/refund",
            data=payload or {},
            headers=build_headers(self.token, key),
        )

    def get_payment(self, payment_id: str) -> APIResponse:
        return self.request.get(
            f"/v1/payments/{payment_id}",
            headers=build_headers(self.token),
        )