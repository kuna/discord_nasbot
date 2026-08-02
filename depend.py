from utils.web import Web
from utils.webproxy import WebProxy


class Dependency:
    def __init__(self, config):
        self.config = config
        # DOH_URL=off falls back to the system resolver
        doh_url = None if config.DOH_URL.lower() == "off" else config.DOH_URL
        self.web = Web(doh_url=doh_url)
        # webproxy is only available when PROXY_HOST is configured
        self.webproxy = (
            WebProxy(config.PROXY_HOST, config.PROXY_PORT, doh_url=doh_url)
            if config.PROXY_HOST
            else None
        )
