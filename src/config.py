from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


class AppConfig(BaseSettings):
    """
    Application Configuration
    """

    # TikTok Settings
    tiktok_url: Optional[str] = Field(
        None, description="URL of the TikTok user or live to record"
    )
    users: List[str] = Field(
        default_factory=list, description="List of TikTok usernames to record"
    )
    room_id: Optional[str] = Field(None, description="Specific Room ID to record")

    # Recording Settings
    mode: str = Field(
        "manual", description="Recording mode: manual, automatic, followers"
    )
    output_dir: str = Field(default=".", description="Directory to save recordings")
    duration: Optional[int] = Field(
        None, description="Maximum duration of recording in seconds"
    )
    check_interval: int = Field(
        5, description="Interval in minutes to check for live (automatic mode)"
    )

    # Network Settings
    proxy: Optional[str] = Field(
        None, description="Proxy URL (e.g., http://user:pass@host:port)"
    )
    cookies_file: str = Field("cookies.json", description="Path to cookies file")

    # Upload Settings
    telegram_enabled: bool = Field(False, description="Enable Telegram upload")
    telegram_api_id: Optional[int] = Field(None, description="Telegram API ID")
    telegram_api_hash: Optional[str] = Field(None, description="Telegram API Hash")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram Chat ID")

    # Logging
    log_level: str = Field("INFO", description="Logging level")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def get_cookies_path(self) -> Path:
        """Resolve cookies file path."""
        path = Path(self.cookies_file)
        if not path.is_absolute():
            return Path(__file__).parent / self.cookies_file
        return path


# Global Config Instance
config = AppConfig()
