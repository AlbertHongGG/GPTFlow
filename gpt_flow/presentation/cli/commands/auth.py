import asyncio
from pathlib import Path

import typer
from rich.table import Table

from gpt_flow.config import config
from gpt_flow.infrastructure.clients.http_client import CurlHttpClient
from gpt_flow.presentation.cli.context import (
    console,
    get_auth_repository,
    setup_logging,
)

auth_app = typer.Typer(name="auth", help="管理與檢視身分憑證")


@auth_app.command("import")
def auth_import(
    file_path: Path = typer.Argument(..., help="HAR 封包檔案或 JSON 憑證路徑"),
) -> None:
    """從 HAR 封包紀錄或 JSON 檔案匯入憑證。"""
    auth_repo = get_auth_repository()
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
    auth_repo = get_auth_repository()
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
    setup_logging(debug)

    async def _run() -> None:
        auth_repo = get_auth_repository()
        http_client = CurlHttpClient(proxy=config.proxy)
        try:
            with console.status(
                "[bold green]正在向 ChatGPT 伺服器刷新 Access Token...[/bold green]"
            ):
                new_creds = await auth_repo.refresh(http_client)
            console.print(
                "[bold green]✓ 成功刷新 Access Token 與 Session Cookies！[/bold green]"
            )
            table = Table(title="更新後的憑證狀態")
            table.add_column("屬性", style="cyan")
            table.add_column("數值", style="green")
            table.add_row("帳號 Email", new_creds.email or "未提供")
            table.add_row("訂閱方案", new_creds.plan_type or "free")
            table.add_row("Cookie 數量", str(len(new_creds.cookies)))
            table.add_row(
                "Token 是否過期",
                "已過期" if new_creds.is_expired() else "有效 (未過期)",
            )
            console.print(table)
        except Exception as e:
            console.print(f"[bold red]✗ 刷新失敗: {e}[/bold red]")
        finally:
            await http_client.close()

    asyncio.run(_run())
