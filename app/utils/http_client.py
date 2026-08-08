import httpx


def get_http_client():
    """
    Returns an HTTP client instance.
    This function can be used to create and return an HTTP client for making requests.
    """
    # Create an instance of httpx.AsyncClient with custom timeout and limits
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(45.0),
        limits=httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=180,
        ),
    )
    return client
