"""The only outbound HTTP in the system: talking to a store's GET /products."""

import httpx

STORE_TIMEOUT_SECONDS = 10


class StoreUnavailableError(Exception):
    """A store's API could not be reached, timed out, or returned an error status."""


class StoreDataError(Exception):
    """A store answered, but the body was not a usable products payload."""


async def fetch_products(api_endpoint: str, name_contains: str | None = None) -> list[dict]:
    """Fetch a store's catalog, optionally filtered by a product-name substring."""
    params = {"name_contains": name_contains} if name_contains else None
    try:
        async with httpx.AsyncClient(timeout=STORE_TIMEOUT_SECONDS) as client:
            response = await client.get(api_endpoint, params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise StoreUnavailableError(f"{api_endpoint}: {exc}") from exc

    try:
        products = response.json()["products"]
    except (ValueError, KeyError, TypeError) as exc:
        raise StoreDataError(f"{api_endpoint}: unexpected response body") from exc

    if not isinstance(products, list):
        raise StoreDataError(f"{api_endpoint}: 'products' is not a list")
    return products
