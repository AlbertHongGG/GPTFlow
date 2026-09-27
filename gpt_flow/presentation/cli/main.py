import sys

import typer

from gpt_flow.presentation.cli.commands import (
    auth_app,
    chat_command,
    session_app,
)

# Ensure proper UTF-8 stdout/stderr handling on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

app = typer.Typer(
    name="gptflow",
    help="GPTFlow: 高性能 ChatGPT Web 逆向工程非同步客戶端與 CLI 工具",
    no_args_is_help=True,
)

# Register top-level command
app.command("chat")(chat_command)

# Register sub-command groups
app.add_typer(auth_app)
app.add_typer(session_app)

if __name__ == "__main__":
    app()
