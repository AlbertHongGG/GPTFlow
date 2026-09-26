import pytest

from gpt_flow.domain.enums import StreamEventType
from gpt_flow.infrastructure.clients.sse_parser import SSEStreamParser


@pytest.mark.asyncio
async def test_sse_parser_text_stream() -> None:
    """Test standard delta_encoding v1 text streaming."""
    lines = [
        'data: "v1"',
        '{"conversation_id": "conv-123"}',
        'data: {"conversation_id": "conv-123"}',
        'data: {"p": "/message/id", "v": "msg-456"}',
        'data: {"v": {"message": {"id": "msg-456", "content": {"content_type": "text"}}}}',
        'data: {"p": "/message/content/parts/0", "o": "append", "v": "Hello"}',
        'data: {"v": ", world!"}',
        'data: {"v": [{"p": "/message/status", "v": "finished_successfully"}]}',
        "data: [DONE]",
    ]

    async def mock_generator():
        for line in lines:
            yield line

    parser = SSEStreamParser()
    chunks = []
    async for chunk in parser.parse_stream(mock_generator()):
        chunks.append(chunk)

    # Filter text content chunks
    content_chunks = [c for c in chunks if c.event_type == StreamEventType.CONTENT]
    assert len(content_chunks) == 2
    assert content_chunks[0].text == "Hello"
    assert content_chunks[1].text == ", world!"
    assert content_chunks[0].conversation_id == "conv-123"
    assert content_chunks[0].message_id == "msg-456"

    # Verify DONE chunk
    done_chunks = [c for c in chunks if c.event_type == StreamEventType.DONE]
    assert len(done_chunks) == 1
    assert done_chunks[0].is_finished is True


@pytest.mark.asyncio
async def test_sse_parser_thinking_stream() -> None:
    """Test streaming thinking/reasoning chunks."""
    lines = [
        'data: {"conversation_id": "conv-reason-1"}',
        'data: {"v": {"message": {"id": "msg-reason-1", "content": {"content_type": "thought"}}}}',
        'data: {"p": "/message/content/thought/parts/0", "o": "append", "v": "Thinking step 1"}',
        'data: {"v": " and step 2"}',
        'data: {"p": "/message/content/parts/0", "o": "append", "v": "Final answer"}',
        "data: [DONE]",
    ]

    async def mock_generator():
        for line in lines:
            yield line

    parser = SSEStreamParser()
    chunks = []
    async for chunk in parser.parse_stream(mock_generator()):
        chunks.append(chunk)

    thinking_chunks = [c for c in chunks if c.event_type == StreamEventType.THINKING]
    assert len(thinking_chunks) == 2
    assert thinking_chunks[0].thinking_text == "Thinking step 1"
    assert thinking_chunks[1].thinking_text == " and step 2"

    content_chunks = [c for c in chunks if c.event_type == StreamEventType.CONTENT]
    assert len(content_chunks) == 1
    assert content_chunks[0].text == "Final answer"


@pytest.mark.asyncio
async def test_sse_parser_error_handling() -> None:
    """Test server error handling in SSE stream."""
    lines = [
        'data: {"error": {"message": "Rate limit reached", "type": "usage_limit"}}',
    ]

    async def mock_generator():
        for line in lines:
            yield line

    parser = SSEStreamParser()
    chunks = []
    async for chunk in parser.parse_stream(mock_generator()):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].event_type == StreamEventType.ERROR
    assert chunks[0].text == "Rate limit reached"
    assert chunks[0].is_finished is True
