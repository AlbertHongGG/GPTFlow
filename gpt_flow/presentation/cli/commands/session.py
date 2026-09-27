import typer
from rich.table import Table

from gpt_flow.presentation.cli.context import (
    console,
    get_session_repository,
)

session_app = typer.Typer(name="session", help="管理本機對話會話")


@session_app.command("list")
def session_list() -> None:
    """列出本機儲存的所有歷史對話會話。"""
    session_repo = get_session_repository()
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
    session_repo = get_session_repository()
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
