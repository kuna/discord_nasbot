from utils.web import Web
from utils.webproxy import WebProxy


class Dependency:
    def __init__(self, config):
        self.config = config
        self.web = Web()
        # webproxy is only available when PROXY_HOST is configured
        self.webproxy = (
            WebProxy(config.PROXY_HOST, config.PROXY_PORT) if config.PROXY_HOST else None
        )
