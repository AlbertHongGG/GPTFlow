import json
import logging
from pathlib import Path

from gpt_flow.domain.entities import AuthCredentials
from gpt_flow.domain.interfaces import IAuthRepository
from gpt_flow.infrastructure.auth.jwt_helper import parse_jwt_claims

logger = logging.getLogger("gpt_flow.auth_store")


class FileAuthRepository(IAuthRepository):
    """File-based repository storing authentication credentials."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.file_path = self.storage_dir / "auth.json"

    def exists(self) -> bool:
        """Check if auth.json exists and is non-empty."""
        return self.file_path.exists() and self.file_path.stat().st_size > 0

    def load(self) -> AuthCredentials | None:
        """Load stored authentication credentials from disk."""
        if not self.exists():
            return None

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            access_token = data.get("access_token", "")
            claims = parse_jwt_claims(access_token) if access_token else {}

            return AuthCredentials(
                access_token=access_token,
                device_id=data.get("device_id")
                or data.get("cookies", {}).get("oai-did", ""),
                cookies=data.get("cookies", {}),
                user_id=claims.get("user_id"),
                account_id=claims.get("account_id"),
                plan_type=claims.get("plan_type", "free"),
                email=claims.get("email"),
                expires_at=claims.get("exp"),
            )
        except Exception as e:
            logger.error(f"Failed to load credentials from {self.file_path}: {e}")
            return None

    def save(self, credentials: AuthCredentials) -> None:
        """Persist authentication credentials to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "access_token": credentials.access_token,
            "device_id": credentials.device_id,
            "cookies": credentials.cookies,
            "user_id": credentials.user_id,
            "account_id": credentials.account_id,
            "plan_type": credentials.plan_type,
            "email": credentials.email,
            "expires_at": credentials.expires_at,
        }
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved credentials to {self.file_path}")

    def import_from_har(self, har_path: Path) -> AuthCredentials | None:
        """Extract credentials and cookies directly from a HAR file."""
        try:
            with open(har_path, "r", encoding="utf-8") as f:
                har = json.load(f)

            access_token = ""
            device_id = ""
            cookies: dict[str, str] = {}

            for entry in har.get("log", {}).get("entries", []):
                req = entry.get("request", {})
                for h in req.get("headers", []):
                    name = h.get("name", "").lower()
                    if name == "authorization" and h.get("value", "").startswith(
                        "Bearer "
                    ):
                        access_token = h.get("value").split("Bearer ")[1].strip()
                    elif name == "oai-device-id":
                        device_id = h.get("value")

                for c in req.get("cookies", []):
                    cookies[c.get("name")] = c.get("value")

                if access_token and device_id:
                    break

            if not device_id and "oai-did" in cookies:
                device_id = cookies["oai-did"]

            if not access_token:
                logger.warning(f"No Bearer Authorization header found in {har_path}")
                return None

            claims = parse_jwt_claims(access_token)
            creds = AuthCredentials(
                access_token=access_token,
                device_id=device_id,
                cookies=cookies,
                user_id=claims.get("user_id"),
                account_id=claims.get("account_id"),
                plan_type=claims.get("plan_type", "free"),
                email=claims.get("email"),
                expires_at=claims.get("exp"),
            )
            self.save(creds)
            return creds
        except Exception as e:
            logger.error(f"Error importing from HAR file {har_path}: {e}")
            return None
