import base64
import json
import time
from typing import Any


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode a JWT payload without signature verification."""
    clean_token = token.strip()
    if clean_token.startswith("Bearer "):
        clean_token = clean_token.split("Bearer ")[1].strip()

    parts = clean_token.split(".")
    if len(parts) < 2:
        raise ValueError(
            "Invalid JWT token format: expected at least 2 dot-separated segments."
        )

    payload_segment = parts[1]
    # Handle base64url padding
    padded = payload_segment + "=" * (-len(payload_segment) % 4)
    decoded_bytes = base64.urlsafe_b64decode(padded)
    return json.loads(decoded_bytes.decode("utf-8"))


def parse_jwt_claims(token: str) -> dict[str, Any]:
    """Extract standard and OpenAI-specific profile claims from JWT."""
    payload = decode_jwt_payload(token)
    auth_claim = payload.get("https://api.openai.com/auth", {})
    profile_claim = payload.get("https://api.openai.com/profile", {})

    return {
        "user_id": auth_claim.get("user_id") or payload.get("sub"),
        "account_id": auth_claim.get("chatgpt_account_id"),
        "plan_type": auth_claim.get("chatgpt_plan_type", "free"),
        "email": profile_claim.get("email"),
        "name": profile_claim.get("name"),
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
        "session_id": payload.get("session_id"),
    }


def is_jwt_expired(token: str, buffer_seconds: int = 60) -> bool:
    """Check if JWT token has expired or is about to expire."""
    try:
        claims = parse_jwt_claims(token)
        exp = claims.get("exp")
        if not exp:
            return False
        return time.time() >= (exp - buffer_seconds)
    except Exception:
        return True
