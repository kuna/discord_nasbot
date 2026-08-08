import pytest

from config import load_config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # load_config() reads .env; keep the developer's file out of these tests
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    for name in (
        "DISCORD_API_TOKEN",
        "DISABLED_PLUGINS",
        "PROXY_HOST",
        "PROXY_PORT",
        "DOWNLOAD_FOLDER",
        "DOH_URL",
        "TEST_CLI_MODE",
    ):
        monkeypatch.delenv(name, raising=False)


def test_token_is_required_by_default():
    with pytest.raises(Exception, match="DISCORD_API_TOKEN"):
        load_config()


def test_token_is_not_required_in_cli_mode(monkeypatch):
    monkeypatch.setenv("TEST_CLI_MODE", "1")

    config = load_config()

    assert config.TEST_CLI_MODE is True
    assert config.DISCORD_API_TOKEN is None


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " True "])
def test_truthy_cli_mode_values(monkeypatch, value):
    monkeypatch.setenv("TEST_CLI_MODE", value)

    assert load_config().TEST_CLI_MODE is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "anything"])
def test_falsy_cli_mode_values(monkeypatch, value):
    monkeypatch.setenv("TEST_CLI_MODE", value)
    monkeypatch.setenv("DISCORD_API_TOKEN", "token")

    assert load_config().TEST_CLI_MODE is False


def test_defaults(monkeypatch):
    monkeypatch.setenv("DISCORD_API_TOKEN", "token")

    config = load_config()

    assert config.DOWNLOAD_FOLDER == "downloads"
    assert config.DOH_URL.startswith("https://")
    assert config.TEST_CLI_MODE is False
