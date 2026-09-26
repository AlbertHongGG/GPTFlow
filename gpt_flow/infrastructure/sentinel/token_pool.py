import asyncio
import logging

from gpt_flow.domain.entities import AuthCredentials, SentinelTokens
from gpt_flow.domain.interfaces import ISentinelSolver

logger = logging.getLogger("gpt_flow.sentinel.pool")


class SentinelTokenPool:
    """Maintains pre-computed Sentinel tokens to eliminate prompt sending latency."""

    def __init__(
        self,
        solver: ISentinelSolver,
        max_age_seconds: int = 240,
    ) -> None:
        self.solver = solver
        self.max_age_seconds = max_age_seconds
        self._cached_tokens: SentinelTokens | None = None
        self._lock = asyncio.Lock()

    async def get_token(self, credentials: AuthCredentials) -> SentinelTokens:
        """Retrieve valid cached tokens or compute new ones immediately."""
        async with self._lock:
            if self._cached_tokens and self._cached_tokens.is_fresh(
                self.max_age_seconds
            ):
                logger.debug("Reusing fresh cached sentinel token.")
                return self._cached_tokens

            logger.info("Sentinel cache expired or empty. Generating fresh tokens...")
            tokens = await self.solver.get_tokens(credentials)
            self._cached_tokens = tokens
            return tokens

    def invalidate(self) -> None:
        """Invalidate the cached tokens."""
        self._cached_tokens = None
