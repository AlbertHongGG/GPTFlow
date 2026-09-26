import json
import logging
from collections.abc import AsyncGenerator

from gpt_flow.domain.entities import ChatResponseChunk
from gpt_flow.domain.enums import StreamEventType

logger = logging.getLogger("gpt_flow.sse")


class SSEStreamParser:
    """Parses ChatGPT's delta_encoding v1 JSON-patch stream."""

    def __init__(self) -> None:
        self.message_id: str | None = None
        self.conversation_id: str | None = None
        self.title: str | None = None
        self._current_target: str = "content"  # "content" or "thought"

    async def parse_stream(
        self,
        line_generator: AsyncGenerator[str, None],
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        """Consume SSE lines and yield structured ChatResponseChunks."""
        async for line in line_generator:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith(":"):
                continue

            if trimmed == "data: [DONE]":
                yield ChatResponseChunk(
                    event_type=StreamEventType.DONE,
                    message_id=self.message_id,
                    conversation_id=self.conversation_id,
                    is_finished=True,
                )
                break

            if not trimmed.startswith("data: "):
                continue

            payload_str = trimmed[6:]
            if payload_str.startswith('"') and payload_str.endswith('"'):
                # delta_encoding version e.g. "v1"
                continue

            try:
                data = json.loads(payload_str)
            except json.JSONDecodeError:
                continue

            if not isinstance(data, dict):
                continue

            # 1. Check for conversation / message metadata
            if "conversation_id" in data and not self.conversation_id:
                self.conversation_id = data["conversation_id"]

            if data.get("type") == "title_generation":
                self.title = data.get("title")
                yield ChatResponseChunk(
                    event_type=StreamEventType.STATUS,
                    conversation_id=self.conversation_id,
                    message_id=self.message_id,
                    metadata={"title": self.title},
                )
                continue

            if data.get("type") == "message_marker" and "message_id" in data:
                self.message_id = data["message_id"]

            # 2. Check for server errors
            if data.get("error"):
                err = data["error"]
                err_msg = err.get("message") if isinstance(err, dict) else str(err)
                yield ChatResponseChunk(
                    event_type=StreamEventType.ERROR,
                    text=err_msg or "Unknown server error",
                    is_finished=True,
                    metadata={"error": err},
                )
                return

            # 3. Check for message object structure (legacy or initial chunk)
            v = data.get("v")
            if isinstance(v, dict) and "message" in v:
                msg_obj = v["message"]
                if "id" in msg_obj:
                    self.message_id = msg_obj["id"]
                content_obj = msg_obj.get("content", {})
                if content_obj.get("content_type") == "thought":
                    self._current_target = "thought"
                else:
                    self._current_target = "content"

            # 4. Handle delta-encoding text streaming
            # Pattern A: {"p": "/message/content/parts/0", "o": "append", "v": "text"}
            # Pattern B: {"v": "continuation text"}
            # Pattern C: {"p": "/message/content/thought/parts/0", ...}
            p = data.get("p")

            if p is not None:
                if p == "/message/id" and isinstance(v, str):
                    self.message_id = v
                    continue

                if "thought" in p:
                    self._current_target = "thought"
                elif "parts" in p:
                    self._current_target = "content"
                else:
                    continue

            if isinstance(v, str):
                if self._current_target == "thought":
                    yield ChatResponseChunk(
                        event_type=StreamEventType.THINKING,
                        thinking_text=v,
                        message_id=self.message_id,
                        conversation_id=self.conversation_id,
                    )
                else:
                    yield ChatResponseChunk(
                        event_type=StreamEventType.CONTENT,
                        text=v,
                        message_id=self.message_id,
                        conversation_id=self.conversation_id,
                    )
                continue

            # 5. Check for completion in patch arrays
            if isinstance(v, list):
                for item in v:
                    if (
                        isinstance(item, dict)
                        and item.get("v") == "finished_successfully"
                    ):
                        yield ChatResponseChunk(
                            event_type=StreamEventType.STATUS,
                            message_id=self.message_id,
                            conversation_id=self.conversation_id,
                            is_finished=True,
                            metadata={"status": "finished_successfully"},
                        )
