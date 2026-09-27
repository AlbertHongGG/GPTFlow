import asyncio

import typer

from gpt_flow.domain.entities import ChatRequest
from gpt_flow.presentation.cli.context import (
    build_chat_service,
    console,
    setup_logging,
)
from gpt_flow.presentation.renderers.rich_stream import RichStreamRenderer


def chat_command(
    prompt: str = typer.Argument(..., help="傳送給 ChatGPT 的提示詞"),
    model: str = typer.Option(
        "auto", "-m", "--model", help="模型型號 (auto, o1, o3-mini)"
    ),
    thinking: bool = typer.Option(
        False, "-t", "--thinking", help="開啟推理思考模式 (CoT)"
    ),
    session_id: str | None = typer.Option(
        None, "-s", "--session", help="接續既有對話會話 ID"
    ),
    debug: bool = typer.Option(False, "-d", "--debug", help="開啟詳細 Debug 日誌"),
) -> None:
    """發送單次提示詞並以串流格式即時輸出回答。"""
    setup_logging(debug)

    async def _run() -> None:
        service, http_client = build_chat_service()
        renderer = RichStreamRenderer(console)

        req = ChatRequest(
            prompt=prompt,
            model=model,
            conversation_id=session_id,
            thinking_enabled=thinking,
        )

        try:
            conv_id: str | None = None
            async for chunk in service.stream_chat(req):
                renderer.handle_chunk(chunk)
                if chunk.conversation_id:
                    conv_id = chunk.conversation_id

            active_id = conv_id or session_id
            if active_id:
                console.print(
                    f"\n[dim]會話 ID: {active_id} (接續對話請加上 -s {active_id})[/dim]"
                )
        finally:
            await http_client.close()

    asyncio.run(_run())
