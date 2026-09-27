from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from gpt_flow.domain.entities import (
    AuthCredentials,
    ChatRequest,
    ChatResponseChunk,
    ConversationTree,
    SentinelTokens,
    TelemetryData,
)


class IHttpClient(ABC):
    """Abstract HTTP client with TLS fingerprint impersonation capability."""

    @abstractmethod
    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> Any:
        """Execute a standard HTTP request."""

    @abstractmethod
    async def stream_lines(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        cookies: dict[str, str] | None = None,
        timeout: float = 120.0,
    ) -> AsyncGenerator[str, None]:
        """Stream response lines (for SSE text/event-stream)."""

    @abstractmethod
    async def close(self) -> None:
        """Close the underlying HTTP session."""


class IAuthRepository(ABC):
    """Persistence repository for credentials and session cookies."""

    @abstractmethod
    def load(self) -> AuthCredentials | None:
        """Load stored authentication credentials."""

    @abstractmethod
    def save(self, credentials: AuthCredentials) -> None:
        """Persist authentication credentials."""

    @abstractmethod
    def exists(self) -> bool:
        """Check if saved credentials exist."""

    @abstractmethod
    async def refresh(self, http_client: "IHttpClient") -> AuthCredentials:
        """Refresh access token and rolling cookies using session endpoint."""


class ISessionRepository(ABC):
    """Persistence repository for conversation session DAGs."""

    @abstractmethod
    def load(self, session_id: str) -> ConversationTree | None:
        """Load conversation tree by session ID."""

    @abstractmethod
    def save(self, conversation: ConversationTree) -> None:
        """Persist conversation tree."""

    @abstractmethod
    def list_sessions(self) -> list[str]:
        """List all available session IDs."""


class ISentinelSolver(ABC):
    """Solver for OpenAI Sentinel defense, PoW, and requirements."""

    @abstractmethod
    async def get_tokens(self, credentials: AuthCredentials) -> SentinelTokens:
        """Acquire fresh sentinel tokens (PoW + requirements)."""

    @abstractmethod
    async def send_ping(
        self,
        credentials: AuthCredentials,
        sentinel_tokens: SentinelTokens,
        seq: int,
        conversation_id: str | None = None,
        last_message_id: str | None = None,
    ) -> None:
        """Send background telemetry ping."""


class IChatClient(ABC):
    """High-level client for ChatGPT conversation API."""

    @abstractmethod
    async def stream_conversation(
        self,
        request: ChatRequest,
        credentials: AuthCredentials,
        sentinel_tokens: SentinelTokens,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        """Stream an LLM response via SSE."""

    @abstractmethod
    async def prepare(
        self,
        request: ChatRequest,
        credentials: AuthCredentials,
        source: str = "context_change",
    ) -> None:
        """Send speculative /prepare call."""

    @abstractmethod
    async def report_telemetry(
        self,
        telemetry: TelemetryData,
        credentials: AuthCredentials,
    ) -> None:
        """Report stream latency and token metrics."""
