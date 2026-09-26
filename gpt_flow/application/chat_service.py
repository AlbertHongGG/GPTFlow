import logging
import time
from collections.abc import AsyncGenerator

from gpt_flow.domain.entities import (
    AuthorRole,
    ChatRequest,
    ChatResponseChunk,
    ConversationTree,
    StreamEventType,
    TelemetryData,
)
from gpt_flow.domain.exceptions import MissingCredentialsError, TokenExpiredError
from gpt_flow.domain.interfaces import (
    IAuthRepository,
    IChatClient,
    ISessionRepository,
)
from gpt_flow.infrastructure.sentinel.token_pool import SentinelTokenPool

logger = logging.getLogger("gpt_flow.service")


class ChatService:
    """Orchestrates conversations, authentication, sentinel defense, and persistence."""

    def __init__(
        self,
        auth_repository: IAuthRepository,
        sentinel_pool: SentinelTokenPool,
        session_repository: ISessionRepository,
        chat_client: IChatClient,
    ) -> None:
        self.auth_repo = auth_repository
        self.sentinel_pool = sentinel_pool
        self.session_repo = session_repository
        self.chat_client = chat_client

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        """
        Send a user prompt and stream the assistant's response.

        Automatically manages authentication, sentinel tokens, and conversation trees.
        """
        # 1. Validate Authentication
        creds = self.auth_repo.load()
        if not creds:
            raise MissingCredentialsError(
                "No credentials found. Please import your cookies or auth token."
            )
        if creds.is_expired():
            raise TokenExpiredError(
                "Access token is expired. Please update credentials."
            )

        # 2. Resolve Conversation Tree and Parent Pointer
        tree: ConversationTree
        if request.conversation_id:
            existing_tree = self.session_repo.load(request.conversation_id)
            if existing_tree:
                tree = existing_tree
                request.parent_message_id = tree.get_parent_id()
            else:
                tree = ConversationTree(conversation_id=request.conversation_id)
                request.parent_message_id = "client-created-root"
        else:
            tree = ConversationTree()
            request.parent_message_id = "client-created-root"

        # Record user message in DAG
        tree.add_message(
            role=AuthorRole.USER,
            content=request.prompt,
            system_hints=["reason"] if request.thinking_enabled else [],
        )

        # 3. Acquire Fresh Sentinel Security Tokens
        sentinel_tokens = await self.sentinel_pool.get_token(creds)

        # 4. Stream Response from Core Engine
        full_text_parts: list[str] = []
        full_thought_parts: list[str] = []
        assistant_msg_id: str | None = None
        assigned_conv_id: str | None = request.conversation_id
        start_time = time.time()
        first_token_time: float | None = None
        token_count = 0

        async for chunk in self.chat_client.stream_conversation(
            request, creds, sentinel_tokens
        ):
            if chunk.conversation_id and not assigned_conv_id:
                assigned_conv_id = chunk.conversation_id
                tree.conversation_id = assigned_conv_id

            if chunk.message_id and not assistant_msg_id:
                assistant_msg_id = chunk.message_id

            if chunk.event_type == StreamEventType.THINKING and chunk.thinking_text:
                full_thought_parts.append(chunk.thinking_text)
                if first_token_time is None:
                    first_token_time = time.time()

            elif chunk.event_type == StreamEventType.CONTENT and chunk.text:
                full_text_parts.append(chunk.text)
                token_count += 1
                if first_token_time is None:
                    first_token_time = time.time()

            yield chunk

        total_time_ms = (time.time() - start_time) * 1000
        first_token_ms = (
            (first_token_time - start_time) * 1000
            if first_token_time
            else total_time_ms
        )

        # 5. Persist Assistant Response in Conversation DAG
        full_text = "".join(full_text_parts)
        full_thought = "".join(full_thought_parts)

        if full_text or full_thought:
            asst_node = tree.add_message(
                role=AuthorRole.ASSISTANT,
                content=full_text,
                thinking_content=full_thought or None,
            )
            if assistant_msg_id:
                # Update node ID with server's message UUID
                del tree.messages[asst_node.id]
                asst_node.id = assistant_msg_id
                tree.messages[assistant_msg_id] = asst_node
                tree.current_node_id = assistant_msg_id

            if tree.conversation_id:
                self.session_repo.save(tree)

        # 6. Report Performance Telemetry
        if assistant_msg_id:
            telemetry = TelemetryData(
                server_request_id=assistant_msg_id,
                model=request.model,
                preflight_time_ms=0.0,
                count_tokens=token_count,
                ts_first_token_ms=first_token_ms,
                ts_total_request_ms=total_time_ms,
            )
            # Send telemetry in background
            try:
                await self.chat_client.report_telemetry(telemetry, creds)
            except Exception as e:
                logger.debug(f"Telemetry submission error: {e}")
