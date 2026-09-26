"""Domain exception hierarchy for GPTFlow."""


class GPTFlowError(Exception):
    """Base exception for all GPTFlow errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(GPTFlowError):
    """Base error for authentication failures."""


class MissingCredentialsError(AuthenticationError):
    """Raised when no access token or session cookies can be found."""


class TokenExpiredError(AuthenticationError):
    """Raised when the access token or session cookie has expired."""


class CloudflareBlockedError(GPTFlowError):
    """Raised when Cloudflare WAF challenges or blocks the connection (403/503)."""


class SentinelError(GPTFlowError):
    """Base error for OpenAI Sentinel security framework."""


class PoWComputationError(SentinelError):
    """Raised when Proof-of-Work computation fails."""


class SentinelChallengeError(SentinelError):
    """Raised when sentinel chat-requirements rejection occurs."""


class RateLimitError(GPTFlowError):
    """Raised when OpenAI API returns 429 Too Many Requests."""


class NetworkTransportError(GPTFlowError):
    """Raised on connection timeout, DNS failure, or network drop."""


class StreamParseError(GPTFlowError):
    """Raised when Server-Sent Events stream chunk cannot be parsed."""


class SessionNotFoundError(GPTFlowError):
    """Raised when requested conversation session cannot be located."""
