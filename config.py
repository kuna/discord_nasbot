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
    TEST_CLI_MODE: bool


TRUE_VALUES = {"1", "true", "yes", "on"}


def _loadenv(name: str, required: bool = False):
    v = os.getenv(name)
    if not v and required:
        raise Exception(f'Env "{name}" is required but is null')
    return v


def _loadbool(name: str):
    return (_loadenv(name) or "").strip().lower() in TRUE_VALUES


def load_config():
    load_dotenv()
    # the CLI test mode never talks to discord, so it needs no token
    test_cli_mode = _loadbool("TEST_CLI_MODE")
    return Config(
        DISCORD_API_TOKEN=_loadenv("DISCORD_API_TOKEN", required=not test_cli_mode),
        DISABLED_PLUGINS=_loadenv("DISABLED_PLUGINS"),
        PROXY_HOST=_loadenv("PROXY_HOST"),
        PROXY_PORT=_loadenv("PROXY_PORT"),
        DOWNLOAD_FOLDER=_loadenv("DOWNLOAD_FOLDER") or "downloads",
        # DNS-over-HTTPS endpoint; set DOH_URL=off to use the system resolver
        DOH_URL=_loadenv("DOH_URL") or DEFAULT_DOH_URL,
        TEST_CLI_MODE=test_cli_mode,
    )
