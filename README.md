# Payments API Automation Framework (Task 2)

A lightweight, scalable API test automation framework built with **Python**, **Pytest**, and **Playwright (`APIRequestContext`)** to validate a stateful Payments API (`create payment → authorize → settle → refund`). Includes an embedded **FastAPI** in-memory mock server for zero-config local and CI execution.

## 1. Architecture & Layering
```text
qa-payments-automation-python/
├── data/
│   └── payment_payloads.py       # Dynamic test data & payload builders
├── services/
│   └── payment_api.py            # Service Object layer wrapping Playwright APIRequestContext
├── tests/
│   ├── conftest.py               # Pytest fixtures (auto-starts FastAPI mock, injects API client)
│   └── test_payment_lifecycle.py # Risk-prioritized functional, negative & idempotency tests
├── utils/
│   └── helpers.py                # UUIDv4 Idempotency-Key generator & auth header builders
├── mock_server.py                # Local stateful FastAPI mock server for the Payments API
├── pytest.ini                    # Pytest configuration & custom test markers
└── requirements.txt              # Project dependencies# qa-payments-automation-python-

