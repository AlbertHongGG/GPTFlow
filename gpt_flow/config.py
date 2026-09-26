from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Global configuration settings for GPTFlow."""

    model_config = SettingsConfigDict(
        env_prefix="GPTFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General / Debug
    debug: bool = Field(default=False, description="Enable verbose debug logging")
    proxy: str | None = Field(default=None, description="HTTP/SOCKS5 Proxy URL")

    # API Endpoints
    base_url: str = Field(default="https://chatgpt.com", description="ChatGPT Base URL")
    backend_api_url: str = Field(
        default="https://chatgpt.com/backend-api", description="ChatGPT Backend API URL"
    )

    # Model & Reasoning Defaults
    default_model: str = Field(
        default="auto", description="Default model (e.g. auto, o1, o3-mini)"
    )
    default_language: str = Field(default="zh-TW", description="Interface language tag")
    default_timezone: str = Field(default="Asia/Taipei", description="Timezone name")
    default_timezone_offset_min: int = Field(
        default=-480, description="Timezone offset in minutes"
    )
    enable_thinking: bool = Field(
        default=False, description="Default thinking / reasoning toggle"
    )

    # Storage Paths
    cookies_dir: Path = Field(
        default=Path("./user_cookies"), description="Path to cookies storage directory"
    )
    sessions_dir: Path = Field(
        default=Path("./sessions"),
        description="Path to conversation sessions directory",
    )

    # Client Identity & Browser Emulation
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        description="Emulated User-Agent header",
    )
    client_version: str = Field(
        default="prod-0d62007364a43c10125c91f7dcc21675e9b9a893",
        description="OpenAI Frontend build version",
    )
    client_build_number: str = Field(
        default="11406653", description="OpenAI Client build number"
    )

    def ensure_directories(self) -> None:
        """Ensure necessary runtime directories exist."""
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)


config = AppConfig()
