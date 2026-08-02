from utils.web import Web


class WebProxy(Web):
    """Web accessor that routes every request through an HTTP proxy (e.g. DPI bypass).

    proxy_host is a hostname or URL, e.g. "dpi.local" or "http://dpi.local:8080".
    proxy_port is appended to the host when given.

    DNS-over-HTTPS lookups are sent through the proxy too. Note that the proxy
    resolves the *target* hostname itself, so doh_url here only covers resolving
    hostnames this client looks up directly. To get DNS-over-HTTPS on the proxied
    path, enable it in the proxy (SpoofDPI: --dns-mode https).
    """

    def __init__(self, proxy_host, proxy_port=None, doh_url=None):
        proxy = proxy_host if "://" in proxy_host else f"http://{proxy_host}"
        if proxy_port:
            proxy = f"{proxy}:{proxy_port}"
        super().__init__(doh_url=doh_url, proxy=proxy)
