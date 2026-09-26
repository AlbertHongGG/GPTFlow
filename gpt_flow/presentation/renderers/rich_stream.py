from rich.console import Console

from gpt_flow.domain.entities import ChatResponseChunk
from gpt_flow.domain.enums import StreamEventType


class RichStreamRenderer:
    """Renders streaming responses with live visual distinction for thinking and content."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._thinking_active = False
        self._thinking_buffer: list[str] = []

    def handle_chunk(self, chunk: ChatResponseChunk) -> None:
        """Process a single incoming chunk and print formatted terminal output."""
        if chunk.event_type == StreamEventType.THINKING:
            if not self._thinking_active:
                self._thinking_active = True
                self.console.print(
                    "\n[bold cyan]🧠 思考思維鏈 (Thinking / Chain-of-Thought):[/bold cyan]"
                )

            self._thinking_buffer.append(chunk.thinking_text)
            self.console.print(
                f"[dim italic]{chunk.thinking_text}[/dim italic]", end=""
            )

        elif chunk.event_type == StreamEventType.CONTENT:
            if self._thinking_active:
                self._thinking_active = False
                self.console.print(
                    "\n\n[bold green]💬 回答內容 (Assistant Response):[/bold green]"
                )

            self.console.print(chunk.text, end="")

        elif chunk.event_type == StreamEventType.ERROR:
            self.console.print(f"\n[bold red]❌ 錯誤: {chunk.text}[/bold red]")

        elif chunk.event_type == StreamEventType.DONE:
            self.console.print()
