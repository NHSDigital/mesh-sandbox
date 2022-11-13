from urllib.parse import urlencode

DEFAULT_MAX_RESULTS = 500


def get_handler_uri(
    path_queries: list[str],
    url_template: str,
    **kwargs,
) -> str:
    qs_parts = tuple(kwargs.items())
    query = urlencode({k: v for k, v in qs_parts if v})

    base_uri: str = "/messageexchange/" + url_template.format(*path_queries)
    return base_uri if not query else f"{base_uri}?{query}"
