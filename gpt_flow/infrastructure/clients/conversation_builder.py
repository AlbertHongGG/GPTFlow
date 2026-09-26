import time
import uuid
from typing import Any

from gpt_flow.domain.entities import ChatRequest


class ConversationPayloadBuilder:
    """Builds the exact JSON payload for ChatGPT /backend-api/f/conversation."""

    def __init__(
        self,
        timezone: str = "Asia/Taipei",
        timezone_offset_min: int = -480,
    ) -> None:
        self.timezone = timezone
        self.timezone_offset_min = timezone_offset_min

    def build_prepare_payload(
        self,
        request: ChatRequest,
        source: str = "context_change",
    ) -> dict[str, Any]:
        """Build payload for /backend-api/f/conversation/prepare."""
        system_hints = ["reason"] if request.thinking_enabled else []
        return {
            "action": "next",
            "conversation_id": request.conversation_id,
            "parent_message_id": request.parent_message_id or "client-created-root",
            "model": request.model,
            "client_prepare_state": "success",
            "client_prepare_dispatch": "immediate",
            "client_prepare_source": source,
            "timezone_offset_min": self.timezone_offset_min,
            "timezone": self.timezone,
            "conversation_mode": {"kind": "primary_assistant"},
            "system_hints": system_hints,
            "model_response_contracts": [
                {
                    "id": "photo_upload_action.v1",
                    "protocol_version": 1,
                    "presets": ["cap:image", "cap:file", "placement:end"],
                }
            ],
            "partial_query": {
                "id": str(uuid.uuid4()),
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": [request.prompt]},
            },
            "supports_buffering": True,
            "supported_encodings": ["v1"],
            "client_contextual_info": {
                "is_dark_mode": False,
                "time_since_loaded": 150,
                "page_height": 887,
                "page_width": 1707,
                "pixel_ratio": 1.5,
                "screen_height": 1067,
                "screen_width": 1707,
                "app_name": "chatgpt.com",
                "has_web_push_capabilities": True,
                "web_push_notification_permission": "default",
            },
            "local_function_names": ["local.continue_in_work"],
        }

    def build_conversation_payload(
        self,
        request: ChatRequest,
        client_message_id: str | None = None,
    ) -> dict[str, Any]:
        """Build payload for /backend-api/f/conversation."""
        msg_id = client_message_id or str(uuid.uuid4())
        system_hints = ["reason"] if request.thinking_enabled else []

        metadata: dict[str, Any] = {
            "serialization_metadata": {"custom_symbol_offsets": []},
            "submission_mode": "manual_send",
        }
        if request.thinking_enabled:
            metadata["system_hints"] = ["reason"]

        payload: dict[str, Any] = {
            "action": "next",
            "messages": [
                {
                    "id": msg_id,
                    "author": {"role": "user"},
                    "create_time": time.time(),
                    "content": {"content_type": "text", "parts": [request.prompt]},
                    "metadata": metadata,
                }
            ],
            "parent_message_id": request.parent_message_id or "client-created-root",
            "model": request.model,
            "client_prepare_state": "success",
            "timezone_offset_min": self.timezone_offset_min,
            "timezone": self.timezone,
            "conversation_mode": {"kind": "primary_assistant"},
            "enable_message_followups": True,
            "system_hints": system_hints,
            "model_response_contracts": [
                {
                    "id": "photo_upload_action.v1",
                    "protocol_version": 1,
                    "presets": ["cap:image", "cap:file", "placement:end"],
                }
            ],
            "supports_buffering": True,
            "supported_encodings": ["v1"],
            "client_contextual_info": {
                "is_dark_mode": False,
                "time_since_loaded": 200,
                "page_height": 887,
                "page_width": 1707,
                "pixel_ratio": 1.5,
                "screen_height": 1067,
                "screen_width": 1707,
                "app_name": "chatgpt.com",
                "has_web_push_capabilities": True,
                "web_push_notification_permission": "default",
            },
            "paragen_cot_summary_display_override": "allow",
            "force_parallel_switch": "auto",
            "local_function_names": ["local.continue_in_work"],
        }

        if request.conversation_id:
            payload["conversation_id"] = request.conversation_id

        return payload
