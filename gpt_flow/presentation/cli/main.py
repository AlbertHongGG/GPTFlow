import asyncio
import logging
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import typer
from rich.console import Console
from rich.table import Table

from gpt_flow.application.chat_service import ChatService
from gpt_flow.config import config
from gpt_flow.domain.entities import ChatRequest
from gpt_flow.infrastructure.clients.chat_client import ChatApiClient
from gpt_flow.infrastructure.clients.http_client import CurlHttpClient
from gpt_flow.infrastructure.sentinel.sentinel_service import SentinelService
from gpt_flow.infrastructure.sentinel.token_pool import SentinelTokenPool
from gpt_flow.infrastructure.storage.file_auth_store import FileAuthRepository
from gpt_flow.infrastructure.storage.file_session_store import FileSessionRepository
from gpt_flow.presentation.renderers.rich_stream import RichStreamRenderer

app = typer.Typer(
    name="gptflow",
    help="GPTFlow: 高性能 ChatGPT Web 逆向工程非同步客戶端與 CLI 工具",
    no_args_is_help=True,
)
auth_app = typer.Typer(name="auth", help="管理與檢視身分憑證")
session_app = typer.Typer(name="session", help="管理本機對話會話")
app.add_typer(auth_app)
app.add_typer(session_app)

console = Console()


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_service(proxy: str | None = None) -> tuple[ChatService, CurlHttpClient]:
    auth_repo = FileAuthRepository(config.cookies_dir)
    session_repo = FileSessionRepository(config.sessions_dir)
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


@app.command("chat")
def chat(
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
    _setup_logging(debug)

    async def _run() -> None:
        service, http_client = _build_service()
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

            if conv_id and not session_id:
                console.print(
                    f"\n[dim]會話 ID: {conv_id} (可使用 -s {conv_id} 接續對話)[/dim]"
                )
        finally:
            await http_client.close()

    asyncio.run(_run())


@app.command("repl")
def repl(
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
        service, http_client = _build_service()
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


@auth_app.command("import")
def auth_import(
    file_path: Path = typer.Argument(..., help="HAR 封包檔案或 JSON 憑證路徑"),
) -> None:
    """從 HAR 封包紀錄或 JSON 檔案匯入憑證。"""
    auth_repo = FileAuthRepository(config.cookies_dir)
    if file_path.suffix.lower() == ".json":
        creds = auth_repo.import_from_har(file_path)
        if creds:
            console.print(
                f"[bold green]✔ 成功從 {file_path.name} 匯入憑證！[/bold green]"
            )
            console.print(f"使用者: {creds.email} ({creds.plan_type})")
            console.print(f"裝置 ID: {creds.device_id}")
            return

    console.print(f"[bold red]❌ 無法從 {file_path} 解析出有效的憑證。[/bold red]")


@auth_app.command("status")
def auth_status() -> None:
    """檢視當前儲存的身分認證與 Token 狀態。"""
    auth_repo = FileAuthRepository(config.cookies_dir)
    creds = auth_repo.load()
    if not creds:
        console.print(
            "[yellow]尚未檢測到有效的憑證。請執行 'gptflow auth import <檔案>'。[/yellow]"
        )
        return

    table = Table(title="GPTFlow 當前身分憑證狀態")
    table.add_column("屬性", style="cyan")
    table.add_column("數值", style="green")

    table.add_row("帳號 Email", creds.email or "未提供")
    table.add_row("使用者 ID", creds.user_id or "未提供")
    table.add_row("訂閱方案", creds.plan_type or "free")
    table.add_row("裝置 ID", creds.device_id)
    table.add_row("Cookie 數量", str(len(creds.cookies)))
    table.add_row("Token 是否過期", "已過期" if creds.is_expired() else "有效 (未過期)")

    console.print(table)


@auth_app.command("refresh")
def auth_refresh(
    debug: bool = typer.Option(False, "--debug", help="開啟詳細除錯日誌"),
) -> None:
    """使用儲存的 Session Cookie 向 ChatGPT 伺服器刷新 Access Token 與 Cookie。"""
    _setup_logging(debug)

    async def _run() -> None:
        auth_repo = FileAuthRepository(config.cookies_dir)
        http_client = CurlHttpClient(proxy=config.proxy)
        try:
            with console.status("[bold green]正在向 ChatGPT 伺服器刷新 Access Token...[/bold green]"):
                new_creds = await auth_repo.refresh(http_client)
            console.print("[bold green]✓ 成功刷新 Access Token 與 Session Cookies！[/bold green]")
            table = Table(title="更新後的憑證狀態")
            table.add_column("屬性", style="cyan")
            table.add_column("數值", style="green")
            table.add_row("帳號 Email", new_creds.email or "未提供")
            table.add_row("訂閱方案", new_creds.plan_type or "free")
            table.add_row("Cookie 數量", str(len(new_creds.cookies)))
            table.add_row("Token 是否過期", "已過期" if new_creds.is_expired() else "有效 (未過期)")
            console.print(table)
        except Exception as e:
            console.print(f"[bold red]✗ 刷新失敗: {e}[/bold red]")
        finally:
            await http_client.close()

    asyncio.run(_run())


@session_app.command("list")
def session_list() -> None:
    """列出本機儲存的所有歷史對話會話。"""
    session_repo = FileSessionRepository(config.sessions_dir)
    sessions = session_repo.list_sessions()

    if not sessions:
        console.print("[dim]目前沒有任何本機會話紀錄。[/dim]")
        return

    table = Table(title="本機對話紀錄清單")
    table.add_column("會話 ID", style="cyan")
    table.add_column("訊息總數", style="magenta")

    for sid in sessions:
        tree = session_repo.load(sid)
        msg_count = len(tree.messages) if tree else 0
        table.add_row(sid, str(msg_count))

    console.print(table)


@session_app.command("show")
def session_show(
    session_id: str = typer.Argument(..., help="會話 ID"),
) -> None:
    """顯示指定對話會話的完整歷史紀錄。"""
    session_repo = FileSessionRepository(config.sessions_dir)
    tree = session_repo.load(session_id)
    if not tree:
        console.print(f"[bold red]找不到會話: {session_id}[/bold red]")
        return

    console.print(f"[bold cyan]會話 ID: {session_id}[/bold cyan]\n")
    for msg in tree.messages.values():
        role_label = (
            "[bold yellow]User[/bold yellow]"
            if msg.role.value == "user"
            else "[bold green]ChatGPT[/bold green]"
        )
        console.print(f"{role_label}:")
        if msg.thinking_content:
            console.print(f"[dim italic]🧠 思考: {msg.thinking_content}[/dim italic]")
        console.print(f"{msg.content}\n")


if __name__ == "__main__":
    app()
