import asyncio

import typer

from gpt_flow.domain.entities import ChatRequest
from gpt_flow.presentation.cli.context import (
    build_chat_service,
    console,
)
from gpt_flow.presentation.renderers.rich_stream import RichStreamRenderer


def repl_command(
    model: str = typer.Option("auto", "-m", "--model", help="預設模型型號"),
    thinking: bool = typer.Option(False, "-t", "--thinking", help="預設開啟思考模式"),
    session_id: str | None = typer.Option(
        None, "-s", "--session", help="載入指定對話 ID"
    ),
) -> None:
    """進入終端多輪互動對話模式 (REPL)。"""
    console.print("[bold green]🌟 歡迎進入 GPTFlow 互動式終端！[/bold green]")
    console.print(
        "[dim]輸入 '/exit' 或 '/quit' 離開，輸入 '/think on|off' 切換思考模式[/dim]\n"
    )

    current_conv_id = session_id
    current_thinking = thinking

    async def _interactive_loop() -> None:
        nonlocal current_conv_id, current_thinking
        service, http_client = build_chat_service()
        renderer = RichStreamRenderer(console)

        try:
            while True:
                mode_str = (
                    "[cyan]Thinking[/cyan]"
                    if current_thinking
                    else "[dim]Standard[/dim]"
                )
                user_input = console.input(
                    f"\n[bold yellow]User ({mode_str})>[/bold yellow] "
                ).strip()
                if not user_input:
                    continue
                if user_input.lower() in ("/exit", "/quit"):
                    console.print("[dim]再見！[/dim]")
                    break
                if user_input.lower() == "/think on":
                    current_thinking = True
                    console.print("[bold cyan]已開啟思考模式。[/bold cyan]")
                    continue
                if user_input.lower() == "/think off":
                    current_thinking = False
                    console.print("[dim]已關閉思考模式。[/dim]")
                    continue

                req = ChatRequest(
                    prompt=user_input,
                    model=model,
                    conversation_id=current_conv_id,
                    thinking_enabled=current_thinking,
                )

                async for chunk in service.stream_chat(req):
                    renderer.handle_chunk(chunk)
                    if chunk.conversation_id:
                        current_conv_id = chunk.conversation_id
        finally:
            await http_client.close()

    asyncio.run(_interactive_loop())
