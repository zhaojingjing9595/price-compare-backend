import httpx

STORE_TIMEOUT_SECONDS = 10.0
class StoreUnavailableError(Exception):
    """A store's API could not be reached or returned an error status."""


async def fetch_products(base_url: str, name_contains: str):
    """Call a store's GET /products."""
    params = {"name_contains": name_contains} if name_contains else {}
    try:
        async with httpx.AsyncClient(timeout=STORE_TIMEOUT_SECONDS) as client:
            response = await client.get(f"{base_url.rstrip('/')}/products", params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise StoreUnavailableError(f"{base_url}: {exc}") from exc

    return response.json().get("products", [])