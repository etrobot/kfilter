import base64
import hashlib
import hmac
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_management.deepsearch import ZAIChatClient
from backend.data_management.deepsearch import create_zai_client_from_config
from backend.config import load_config_json, get_zai_client_config


def _expected_signature(signature_key: str, params: dict[str, str], content: str, expire_minutes: int) -> str:
    request_time = int(params["timestamp"])
    signature_expire = request_time // (expire_minutes * 60 * 1000)
    signature_1 = hmac.new(
        signature_key.encode("utf-8"),
        str(signature_expire).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    content_encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    signature_params = ",".join(f"{k},{params[k]}" for k in sorted(params))
    signature_2_plain = f"{signature_params}|{content_encoded}|{str(request_time)}"

    return hmac.new(
        signature_1.encode("utf-8"),
        signature_2_plain.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def test_get_headers_with_signature_generates_expected_signature():
    config = {
        "bearer_token": "test-token",
        "user_id": "user",
        "signature_key": "secret",
        "signature_expire_minutes": 5,
    }
    client = ZAIChatClient(config=config)

    params = {
        "timestamp": "1716400000000",
        "requestId": "11111111-1111-1111-1111-111111111111",
        "user_id": "user",
    }
    content = "hello"

    headers = client._get_headers_with_signature(params["timestamp"], params, content)  # pylint: disable=protected-access

    expected_signature = _expected_signature(
        signature_key=config["signature_key"],
        params=params,
        content=content,
        expire_minutes=config["signature_expire_minutes"],
    )

    assert headers["Authorization"] == f"Bearer {config['bearer_token']}"
    assert headers["X-Signature"] == expected_signature
    assert "X-Signature" not in client.base_headers


def test_create_client_from_config_uses_backend_config_json():
    cfg = load_config_json()
    client = create_zai_client_from_config()

    assert client is not None, "ZAI client should be created from config.json"
    # Validate core fields match config.json without printing secrets
    assert client.bearer_token == (cfg.get("ZAI_BEARER_TOKEN") or "").strip()
    assert client.user_id == (cfg.get("ZAI_USER_ID") or "").strip()
    assert client.base_url == cfg.get("ZAI_BASE_URL", "https://chat.z.ai")
    assert client.base_headers.get("Authorization", "").startswith("Bearer ")


def test_client_timeouts_match_config_defaults():
    client = create_zai_client_from_config()
    assert client is not None

    cfg = get_zai_client_config()
    assert client.timeout == (
        cfg.get("connect_timeout", 30),
        cfg.get("read_timeout", 180),
    )
