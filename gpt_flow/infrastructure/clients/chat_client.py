import logging
from collections.abc import AsyncGenerator

from gpt_flow.domain.entities import (
    AuthCredentials,
    ChatRequest,
    ChatResponseChunk,
    SentinelTokens,
    TelemetryData,
)
from gpt_flow.domain.interfaces import IChatClient, IHttpClient
from gpt_flow.infrastructure.clients.conversation_builder import (
    ConversationPayloadBuilder,
)
from gpt_flow.infrastructure.clients.sse_parser import SSEStreamParser

logger = logging.getLogger("gpt_flow.chat_client")


class ChatApiClient(IChatClient):
    """Client for ChatGPT Web conversational API and telemetry endpoints."""

    def __init__(
        self,
        http_client: IHttpClient,
        backend_api_url: str = "https://chatgpt.com/backend-api",
        builder: ConversationPayloadBuilder | None = None,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ) -> None:
        self.http_client = http_client
        self.backend_api_url = backend_api_url
        self.builder = builder or ConversationPayloadBuilder()
        self.user_agent = user_agent

    def _get_base_headers(self, credentials: AuthCredentials) -> dict[str, str]:
        return {
            "authorization": f"Bearer {credentials.access_token}",
            "oai-device-id": credentials.device_id,
            "oai-language": self.builder.timezone.split("/")[0],
            "content-type": "application/json",
            "origin": "https://chatgpt.com",
            "referer": "https://chatgpt.com/",
            "user-agent": self.user_agent,
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }

    async def prepare(
        self,
        request: ChatRequest,
        credentials: AuthCredentials,
        source: str = "context_change",
    ) -> str | None:
        """Send speculative prepare request and return conduit_token."""
        url = f"{self.backend_api_url}/f/conversation/prepare"
        payload = self.builder.build_prepare_payload(request, source=source)
        headers = self._get_base_headers(credentials)
        headers["accept"] = "*/*"

        try:
            resp = await self.http_client.request(
                method="POST",
                url=url,
                headers=headers,
                json=payload,
                cookies=credentials.cookies,
            )
            data = resp.json()
            conduit_token = data.get("conduit_token")
            logger.debug(
                f"Prepare call succeeded, conduit_token obtained: {bool(conduit_token)}"
            )
            return conduit_token
        except Exception as e:
            logger.warning(
                f"Prepare call failed (will continue without conduit_token): {e}"
            )
            return None

    async def stream_conversation(
        self,
        request: ChatRequest,
        credentials: AuthCredentials,
        sentinel_tokens: SentinelTokens,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        """Stream conversational response via Server-Sent Events (SSE)."""
        # Step 1: Speculative prepare to acquire live conduit_token
        conduit_token = await self.prepare(
            request, credentials, source="context_change"
        )

        # Step 2: Build conversation payload & headers
        conv_payload = self.builder.build_conversation_payload(request)
        headers = self._get_base_headers(credentials)
        headers.update(
            {
                "accept": "text/event-stream",
                "openai-sentinel-chat-requirements-token": sentinel_tokens.chat_requirements_token,
                "openai-sentinel-proof-token": sentinel_tokens.proof_token,
                "x-openai-web-frontend": "core_web",
                "x-openai-target-path": "/backend-api/f/conversation",
                "x-openai-target-route": "/backend-api/f/conversation",
            }
        )

        if conduit_token:
            headers["x-conduit-token"] = conduit_token
        if sentinel_tokens.turnstile_token:
            headers["openai-sentinel-turnstile-token"] = sentinel_tokens.turnstile_token

        conv_url = f"{self.backend_api_url}/f/conversation"
        logger.info(
            f"Initiating conversation stream (thinking={request.thinking_enabled}, model={request.model})..."
        )

        raw_line_stream = self.http_client.stream_lines(
            method="POST",
            url=conv_url,
            headers=headers,
            json=conv_payload,
            cookies=credentials.cookies,
            timeout=120.0,
        )

        parser = SSEStreamParser()
        async for chunk in parser.parse_stream(raw_line_stream):
            yield chunk

    async def report_telemetry(
        self,
        telemetry: TelemetryData,
        credentials: AuthCredentials,
    ) -> None:
        """Report stream latency and token metrics to /lat/r."""
        url = f"{self.backend_api_url}/lat/r"
        headers = self._get_base_headers(credentials)
        headers["accept"] = "*/*"

        body = {
            "server_request_id": telemetry.server_request_id,
            "model": telemetry.model,
            "preflight_time_ms": telemetry.preflight_time_ms,
            "count_tokens": telemetry.count_tokens,
            "ts_first_token_ms": telemetry.ts_first_token_ms,
            "ts_max_token_time_ms": telemetry.ts_max_token_time_ms,
            "ts_mean_token_without_first_ms": telemetry.ts_mean_token_without_first_ms,
            "ts_total_request_ms": telemetry.ts_total_request_ms,
        }

        try:
            await self.http_client.request(
                method="POST",
                url=url,
                headers=headers,
                json=body,
                cookies=credentials.cookies,
            )
            logger.debug(
                f"Telemetry reported successfully for {telemetry.server_request_id}"
            )
        except Exception as e:
            logger.debug(f"Telemetry report ignored error: {e}")
