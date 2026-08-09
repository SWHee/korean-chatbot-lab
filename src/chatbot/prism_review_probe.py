import httpx


def fetch_probe_status() -> str:
    response = httpx.get("https://example.com")
    return response.text
