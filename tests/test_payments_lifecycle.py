import pytest
from services.payment_api import PaymentAPI
from data.payment_payloads import get_valid_payment_payload
from utils.helpers import generate_idempotency_key


@pytest.mark.smoke
def test_full_payment_lifecycle_happy_path(payment_api: PaymentAPI):
    """
    Scenario 1: Happy Path - Complete Payment Lifecycle (Create -> Authorize -> Settle -> Refund)
    Given a valid payment payload in CAD
    When the payment is created, authorized, settled, and subsequently refunded
    Then each state transition succeeds with accurate status codes and ledger states
    """
    payload = get_valid_payment_payload(amount=150.00, currency="CAD")

    # 1. Create Payment
    create_res = payment_api.create_payment(payload)
    assert create_res.status == 201
    payment_data = create_res.json()
    payment_id = payment_data["id"]
    assert payment_data["state"] == "CREATED"

    # 2. Authorize Payment
    auth_res = payment_api.authorize_payment(payment_id)
    assert auth_res.status == 200
    assert auth_res.json()["state"] == "AUTHORIZED"

    # 3. Settle Payment
    settle_res = payment_api.settle_payment(payment_id)
    assert settle_res.status == 200
    assert settle_res.json()["state"] == "SETTLED"

    # 4. Refund Payment
    refund_res = payment_api.refund_payment(payment_id, {"amount": 150.00})
    assert refund_res.status == 200
    assert refund_res.json()["state"] == "REFUNDED"


@pytest.mark.idempotency
def test_duplicate_payment_creation_idempotency(payment_api: PaymentAPI):
    """
    Scenario 2: Idempotency - Duplicate Payment Requests Return Identical Transaction
    Given a valid payment payload and a fixed Idempotency-Key
    When the exact same POST /v1/payments request is sent twice
    Then only one payment record is created and both responses return the same payment ID
    """
    idempotency_key = generate_idempotency_key()
    payload = get_valid_payment_payload(amount=500.00)

    first_res = payment_api.create_payment(payload, idempotency_key=idempotency_key)
    assert first_res.status == 201
    first_body = first_res.json()

    # Replay the exact request with the same idempotency key
    second_res = payment_api.create_payment(payload, idempotency_key=idempotency_key)
    assert second_res.status in (200, 201)
    second_body = second_res.json()

    assert first_body["id"] == second_body["id"]
    assert first_body["amount"] == second_body["amount"]


@pytest.mark.negative
def test_reject_refund_on_unsettled_payment(payment_api: PaymentAPI):
    """
    Scenario 3: Invalid State Transition - Cannot Refund an Unsettled Payment
    Given a payment that has been CREATED and AUTHORIZED, but NOT SETTLED
    When a refund request is submitted for that payment
    Then the API rejects the transition with 422 Unprocessable Entity
    """
    create_res = payment_api.create_payment(get_valid_payment_payload())
    payment_id = create_res.json()["id"]

    payment_api.authorize_payment(payment_id)

    # Attempt premature refund before settlement
    refund_res = payment_api.refund_payment(payment_id)
    assert refund_res.status == 422
    error_body = refund_res.json()
    assert "must be SETTLED" in error_body.get("message", "")


@pytest.mark.negative
def test_reject_over_refund_exceeding_settled_amount(payment_api: PaymentAPI):
    """
    Scenario 4: Financial Boundary Validation - Refund Exceeding Settled Amount
    Given a payment settled for 100.00 CAD
    When a refund request is submitted for 150.00 CAD
    Then the API returns 422 Unprocessable Entity and preserves the SETTLED state
    """
    create_res = payment_api.create_payment(get_valid_payment_payload(amount=100.00))
    payment_id = create_res.json()["id"]

    payment_api.authorize_payment(payment_id)
    payment_api.settle_payment(payment_id)

    # Attempt to refund more than the settled amount
    over_refund_res = payment_api.refund_payment(payment_id, {"amount": 150.00})
    assert over_refund_res.status == 422

    # Verify ledger state remains SETTLED
    get_res = payment_api.get_payment(payment_id)
    assert get_res.json()["state"] == "SETTLED"


@pytest.mark.negative
def test_unauthorized_request_rejected(api_context):
    """
    Scenario 5: Security - Request With Invalid Bearer Token Is Rejected
    Given a PaymentAPI client initialized with an invalid/expired Bearer token
    When a create payment request is sent
    Then the API rejects the request with 401 Unauthorized
    """
    unauthenticated_api = PaymentAPI(
        request_context=api_context, token="invalid-or-expired-token"
    )
    res = unauthenticated_api.create_payment(get_valid_payment_payload())
    assert res.status == 401