import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Self

from curl_cffi.requests import AsyncSession, Response

from gpt_flow.domain.exceptions import (
    CloudflareBlockedError,
    NetworkTransportError,
    RateLimitError,
    TokenExpiredError,
)
from gpt_flow.domain.interfaces import IHttpClient

logger = logging.getLogger("gpt_flow.http")


@dataclass
class HttpResponse:
    """Represents a standard HTTP response."""

    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    text: str = ""
    cookies: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        """Parse response text as JSON."""
        return json.loads(self.text)


class CurlHttpClient(IHttpClient):
    """Async HTTP Client utilizing curl_cffi for browser TLS/JA3 impersonation."""

    def __init__(
        self,
        impersonate: str = "chrome131",
        proxy: str | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.impersonate = impersonate
        self.proxy = proxy
        self.default_headers = default_headers or {}
        self._session: AsyncSession | None = None

    async def _get_session(self) -> AsyncSession:
        """Get or initialize the underlying AsyncSession."""
        if self._session is None:
            self._session = AsyncSession(
                impersonate=self.impersonate,
                proxy=self.proxy,
            )
        return self._session

    def _check_status(self, status: int, text: str) -> None:
        """Check response status and raise domain-specific exceptions."""
        if status == 401:
            raise TokenExpiredError(
                "Session or access token is expired or unauthorized (401)."
            )
        if status == 429:
            raise RateLimitError("Rate limit exceeded or too many requests (429).")
        if status in (403, 503) and (
            "cf-ray" in text
            or "challenge-platform" in text
            or "Just a moment..." in text
        ):
            raise CloudflareBlockedError(
                f"Blocked by Cloudflare security challenge (Status {status})."
            )

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> HttpResponse:
        """Execute a standard HTTP request."""
        session = await self._get_session()
        merged_headers = {**self.default_headers, **(headers or {})}

        try:
            resp: Response = await session.request(
                method=method,
                url=url,
                headers=merged_headers,
                json=json,
                cookies=cookies,
                timeout=timeout,
            )

            text = resp.text
            self._check_status(resp.status_code, text)

            resp_cookies = (
                {k: v for k, v in resp.cookies.items()} if resp.cookies else {}
            )
            return HttpResponse(
                status_code=resp.status_code,
                headers={k.lower(): v for k, v in resp.headers.items()},
                text=text,
                cookies=resp_cookies,
            )
        except (TokenExpiredError, RateLimitError, CloudflareBlockedError):
            raise
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            raise NetworkTransportError(
                f"Network error during {method} {url}: {e}"
            ) from e

    async def stream_lines(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float = 120.0,
    ) -> AsyncGenerator[str, None]:
        """Stream response lines for SSE text/event-stream."""
        session = await self._get_session()
        merged_headers = {**self.default_headers, **(headers or {})}

        try:
            resp: Response = await session.request(
                method=method,
                url=url,
                headers=merged_headers,
                json=json,
                cookies=cookies,
                timeout=timeout,
                stream=True,
            )

            self._check_status(resp.status_code, "")

            async for line_bytes in resp.aiter_lines():
                if line_bytes:
                    yield line_bytes.decode("utf-8", errors="replace")
        except (TokenExpiredError, RateLimitError, CloudflareBlockedError):
            raise
        except Exception as e:
            logger.error(f"Stream error: {e}")
            raise NetworkTransportError(
                f"Stream interrupted during {method} {url}: {e}"
            ) from e

    async def close(self) -> None:
        """Close the AsyncSession."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()
