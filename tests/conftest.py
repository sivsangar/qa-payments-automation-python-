import os
import time
import socket
import subprocess
import sys
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Playwright, APIRequestContext
from services.payment_api import PaymentAPI

load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def local_mock_server():
    """Start an isolated local mock server for this test session."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        port = server_socket.getsockname()[1]

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mock_server:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        for _ in range(50):
            if proc.poll() is not None:
                raise RuntimeError("Local mock server exited before becoming ready")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Local mock server did not become ready within 5 seconds")

        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


@pytest.fixture(scope="session")
def base_url(local_mock_server: str) -> str:
    return local_mock_server


@pytest.fixture(scope="session")
def auth_token() -> str:
    return os.getenv("API_BEARER_TOKEN", "mock-jwt-token")


@pytest.fixture(scope="function")
def api_context(playwright: Playwright, base_url: str) -> APIRequestContext:
    """Creates an isolated Playwright APIRequestContext per test."""
    context = playwright.request.new_context(base_url=base_url)
    yield context
    context.dispose()


@pytest.fixture(scope="function")
def payment_api(api_context: APIRequestContext, auth_token: str) -> PaymentAPI:
    """Provides an initialized PaymentAPI service client to tests."""
    return PaymentAPI(request_context=api_context, token=auth_token)