from config import Config
from depend import Dependency
from utils.doh import DEFAULT_DOH_URL
from utils.web import Web
from utils.webproxy import WebProxy


def make_config(proxy_host=None, proxy_port=None, doh_url=DEFAULT_DOH_URL):
    return Config(
        DISCORD_API_TOKEN="token",
        DISABLED_PLUGINS=None,
        PROXY_HOST=proxy_host,
        PROXY_PORT=proxy_port,
        DOWNLOAD_FOLDER="downloads",
        DOH_URL=doh_url,
        TEST_CLI_MODE=False,
    )


def test_web_is_always_available():
    dep = Dependency(make_config())
    assert isinstance(dep.web, Web)


def test_webproxy_absent_without_proxy_host():
    dep = Dependency(make_config())
    assert dep.webproxy is None


def test_webproxy_created_with_proxy_host():
    dep = Dependency(make_config(proxy_host="dpi.local", proxy_port="8080"))
    assert isinstance(dep.webproxy, WebProxy)
    assert dep.webproxy._proxy == "http://dpi.local:8080"


def test_doh_is_enabled_by_default():
    dep = Dependency(make_config(proxy_host="dpi.local"))
    assert dep.web._resolver is not None
    assert dep.webproxy._resolver is not None


def test_doh_off_falls_back_to_system_resolver():
    dep = Dependency(make_config(proxy_host="dpi.local", doh_url="off"))
    assert dep.web._resolver is None
    assert dep.webproxy._resolver is None


def test_config_is_exposed():
    config = make_config()
    assert Dependency(config).config is config
