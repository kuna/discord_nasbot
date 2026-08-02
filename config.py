import os
from dataclasses import dataclass

from dotenv import load_dotenv

from utils.doh import DEFAULT_DOH_URL


@dataclass
class Config:
    DISCORD_API_TOKEN: str
    DISABLED_PLUGINS: str
    PROXY_HOST: str
    PROXY_PORT: str
    DOWNLOAD_FOLDER: str
    DOH_URL: str


def _loadenv(name: str, required: bool = False):
    v = os.getenv(name)
    if not v and required:
        raise Exception(f'Env "{name}" is required but is null')
    return v


def load_config():
    load_dotenv()
    return Config(
        DISCORD_API_TOKEN=_loadenv("DISCORD_API_TOKEN", True),
        DISABLED_PLUGINS=_loadenv("DISABLED_PLUGINS"),
        PROXY_HOST=_loadenv("PROXY_HOST"),
        PROXY_PORT=_loadenv("PROXY_PORT"),
        DOWNLOAD_FOLDER=_loadenv("DOWNLOAD_FOLDER") or "downloads",
        # DNS-over-HTTPS endpoint; set DOH_URL=off to use the system resolver
        DOH_URL=_loadenv("DOH_URL") or DEFAULT_DOH_URL,
    )
