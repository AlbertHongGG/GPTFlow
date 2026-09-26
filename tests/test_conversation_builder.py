from gpt_flow.domain.entities import ChatRequest
from gpt_flow.infrastructure.clients.conversation_builder import (
    ConversationPayloadBuilder,
)


class TestConversationBuilder:
    """Test conversation payload construction for prepare and conversation endpoints."""

    def test_build_prepare_payload_basic(self) -> None:
        builder = ConversationPayloadBuilder(
            timezone="Asia/Taipei", timezone_offset_min=-480
        )
        req = ChatRequest(
            prompt="Hello World",
            model="auto",
            thinking_enabled=False,
        )
        payload = builder.build_prepare_payload(req)

        assert payload["action"] == "next"
        assert payload["model"] == "auto"
        assert payload["timezone"] == "Asia/Taipei"
        assert payload["timezone_offset_min"] == -480
        assert payload["system_hints"] == []
        assert payload["partial_query"]["content"]["parts"] == ["Hello World"]

    def test_build_prepare_payload_with_thinking(self) -> None:
        builder = ConversationPayloadBuilder()
        req = ChatRequest(
            prompt="Solve math problem",
            model="auto",
            thinking_enabled=True,
            conversation_id="conv-abc",
            parent_message_id="msg-parent-1",
        )
        payload = builder.build_prepare_payload(req)

        assert payload["system_hints"] == ["reason"]
        assert payload["conversation_id"] == "conv-abc"
        assert payload["parent_message_id"] == "msg-parent-1"

    def test_build_conversation_payload_with_thinking(self) -> None:
        builder = ConversationPayloadBuilder()
        req = ChatRequest(
            prompt="Think deeply",
            model="auto",
            thinking_enabled=True,
            conversation_id="conv-xyz",
            parent_message_id="msg-leaf-1",
        )
        payload = builder.build_conversation_payload(
            req, client_message_id="msg-client-1"
        )

        assert payload["action"] == "next"
        assert payload["conversation_id"] == "conv-xyz"
        assert payload["parent_message_id"] == "msg-leaf-1"
        assert payload["system_hints"] == ["reason"]

        # Check message content and metadata
        messages = payload["messages"]
        assert len(messages) == 1
        msg = messages[0]
        assert msg["id"] == "msg-client-1"
        assert msg["content"]["parts"] == ["Think deeply"]
        assert msg["metadata"]["system_hints"] == ["reason"]
