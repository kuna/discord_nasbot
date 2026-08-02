from utils.web import Web


class WebProxy(Web):
    """Web accessor that routes every request through an HTTP proxy (e.g. DPI bypass).

    proxy_host is a hostname or URL, e.g. "dpi.local" or "http://dpi.local:8080".
    proxy_port is appended to the host when given.
    """

    def __init__(self, proxy_host, proxy_port=None):
        super().__init__()
        proxy = proxy_host if "://" in proxy_host else f"http://{proxy_host}"
        if proxy_port:
            proxy = f"{proxy}:{proxy_port}"
        self._proxy = proxy
