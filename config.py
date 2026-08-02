import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    DISCORD_API_TOKEN: str
    DISABLED_PLUGINS: str


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
    )
