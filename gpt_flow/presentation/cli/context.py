import logging

from rich.console import Console

from gpt_flow.application.chat_service import ChatService
from gpt_flow.config import config
from gpt_flow.infrastructure.clients.chat_client import ChatApiClient
from gpt_flow.infrastructure.clients.http_client import CurlHttpClient
from gpt_flow.infrastructure.sentinel.sentinel_service import SentinelService
from gpt_flow.infrastructure.sentinel.token_pool import SentinelTokenPool
from gpt_flow.infrastructure.storage.file_auth_store import FileAuthRepository
from gpt_flow.infrastructure.storage.file_session_store import FileSessionRepository

console = Console()


def setup_logging(debug: bool) -> None:
    """Configure terminal logging format and level."""
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def get_auth_repository() -> FileAuthRepository:
    """Return configured authentication repository."""
    return FileAuthRepository(config.cookies_dir)


def get_session_repository() -> FileSessionRepository:
    """Return configured session repository."""
    return FileSessionRepository(config.sessions_dir)


def build_chat_service(
    proxy: str | None = None,
) -> tuple[ChatService, CurlHttpClient]:
    """Factory creating fully wired ChatService and its underlying CurlHttpClient."""
    auth_repo = get_auth_repository()
    session_repo = get_session_repository()
    http_client = CurlHttpClient(proxy=proxy or config.proxy)
    sentinel_solver = SentinelService(
        http_client, backend_api_url=config.backend_api_url
    )
    sentinel_pool = SentinelTokenPool(sentinel_solver)
    chat_client = ChatApiClient(http_client, backend_api_url=config.backend_api_url)

    service = ChatService(
        auth_repository=auth_repo,
        sentinel_pool=sentinel_pool,
        session_repository=session_repo,
        chat_client=chat_client,
        http_client=http_client,
    )
    return service, http_client
