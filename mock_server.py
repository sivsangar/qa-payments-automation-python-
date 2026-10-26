import os
import uuid
from typing import Any, Dict, Optional
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Mock Payments & Ledger API", version="1.0.0")

# In-memory storage for stateful test execution
PAYMENTS_DB: Dict[str, Dict[str, Any]] = {}
IDEMPOTENCY_STORE: Dict[str, Dict[str, Any]] = {}

VALID_TOKEN = os.getenv("API_BEARER_TOKEN", "mock-jwt-token")


class CreatePaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    source_account: str
    destination_account: str
    description: Optional[str] = None


class RefundPaymentRequest(BaseModel):
    amount: Optional[float] = None


def verify_auth(authorization: Optional[str]) -> None:
    if not authorization or authorization != f"Bearer {VALID_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or expired token")


@app.post("/v1/payments")
def create_payment(
    payload: CreatePaymentRequest,
    authorization: Optional[str] = Header(default=None),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    verify_auth(authorization)

    if not idempotency_key:
        return JSONResponse(
            status_code=400,
            content={"message": "Missing required Idempotency-Key header"},
        )

    # Idempotency replay protection: return cached transaction if key already exists
    if idempotency_key in IDEMPOTENCY_STORE:
        return JSONResponse(
            status_code=200,
            content=IDEMPOTENCY_STORE[idempotency_key],
        )

    payment_id = f"pay_{uuid.uuid4().hex[:10]}"
    payment_record = {
        "id": payment_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "source_account": payload.source_account,
        "destination_account": payload.destination_account,
        "description": payload.description,
        "state": "CREATED",
    }

    PAYMENTS_DB[payment_id] = payment_record
    IDEMPOTENCY_STORE[idempotency_key] = payment_record

    return JSONResponse(status_code=201, content=payment_record)


@app.post("/v1/payments/{payment_id}/authorize")
def authorize_payment(
    payment_id: str,
    authorization: Optional[str] = Header(default=None),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    verify_auth(authorization)

    payment = PAYMENTS_DB.get(payment_id)
    if not payment:
        return JSONResponse(status_code=404, content={"message": "Payment not found"})

    if payment["state"] != "CREATED":
        return JSONResponse(
            status_code=422,
            content={"message": f"Cannot authorize payment in {payment['state']} state. Payment must be CREATED."},
        )

    payment["state"] = "AUTHORIZED"
    return JSONResponse(status_code=200, content=payment)


@app.post("/v1/payments/{payment_id}/settle")
def settle_payment(
    payment_id: str,
    authorization: Optional[str] = Header(default=None),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    verify_auth(authorization)

    payment = PAYMENTS_DB.get(payment_id)
    if not payment:
        return JSONResponse(status_code=404, content={"message": "Payment not found"})

    if payment["state"] != "AUTHORIZED":
        return JSONResponse(
            status_code=422,
            content={"message": f"Cannot settle payment in {payment['state']} state. Payment must be AUTHORIZED."},
        )

    payment["state"] = "SETTLED"
    return JSONResponse(status_code=200, content=payment)


@app.post("/v1/payments/{payment_id}/refund")
def refund_payment(
    payment_id: str,
    payload: Optional[RefundPaymentRequest] = None,
    authorization: Optional[str] = Header(default=None),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    verify_auth(authorization)

    payment = PAYMENTS_DB.get(payment_id)
    if not payment:
        return JSONResponse(status_code=404, content={"message": "Payment not found"})

    # State machine guard: only SETTLED payments can be refunded
    if payment["state"] != "SETTLED":
        return JSONResponse(
            status_code=422,
            content={"message": f"Cannot refund payment in {payment['state']} state; payment must be SETTLED."},
        )

    # Financial boundary guard: cannot refund more than settled amount
    refund_amount = payload.amount if (payload and payload.amount is not None) else payment["amount"]
    if refund_amount > payment["amount"]:
        return JSONResponse(
            status_code=422,
            content={"message": "Refund amount exceeds settled amount."},
        )

    payment["state"] = "REFUNDED"
    payment["refunded_amount"] = refund_amount
    return JSONResponse(status_code=200, content=payment)


@app.get("/v1/payments/{payment_id}")
def get_payment(
    payment_id: str,
    authorization: Optional[str] = Header(default=None),
):
    verify_auth(authorization)

    payment = PAYMENTS_DB.get(payment_id)
    if not payment:
        return JSONResponse(status_code=404, content={"message": "Payment not found"})

    return JSONResponse(status_code=200, content=payment)