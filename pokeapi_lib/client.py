# pokeapi_lib/client.py
import httpx
import logging
from typing import Optional, Dict, Any, Tuple
from .exceptions import ResourceNotFoundError, PokeAPIConnectionError

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://pokeapi.co/api/v2"
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=7.0) # Slightly longer default timeout

# --- Client Management ---
# Option 1: Global client (simpler for basic use, less flexible)
# _client: Optional[httpx.AsyncClient] = None

# def get_client(base_url: str = DEFAULT_BASE_URL, timeout: httpx.Timeout = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
#     global _client
#     if _client is None or _client.base_url != base_url: # Recreate if base_url changes
#          logger.info(f"Creating shared httpx client for base URL: {base_url}")
#          _client = httpx.AsyncClient(base_url=base_url, timeout=timeout, follow_redirects=True)
#     return _client

# async def close_client():
#     global _client
#     if _client:
#          await _client.aclose()
#          _client = None
#          logger.info("Shared httpx client closed.")

# Option 2: Pass client instance (more explicit, better control)
# We'll use this approach. The user of the library manages the client lifecycle.

async def fetch_resource(
    endpoint: str,
    client: httpx.AsyncClient,
    base_url: str = DEFAULT_BASE_URL
) -> Dict[str, Any]:
    """
    Fetches a resource from PokeAPI using a provided httpx client.

    Args:
        endpoint: The specific API endpoint path (e.g., "/pokemon/pikachu").
        client: An active httpx.AsyncClient instance.
        base_url: The base URL for the API (used if endpoint is relative).

    Returns:
        A dictionary containing the JSON response.

    Raises:
        ResourceNotFoundError: If the resource returns a 404 status.
        PokeAPIConnectionError: For network errors, timeouts, or non-404 HTTP errors.
        Exception: For unexpected errors during the request or JSON parsing.
    """
    url = endpoint
    if not endpoint.startswith("http"):
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    logger.debug(f"Fetching data from PokeAPI: {url}")
    try:
        response = await client.get(url)
        response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx
        logger.debug(f"Successfully fetched data from {url}, status: {response.status_code}")
        return response.json() # Assume valid JSON for successful requests

    except httpx.TimeoutException as e:
        logger.error(f"Request timed out for PokeAPI endpoint: {url}", exc_info=True)
        raise PokeAPIConnectionError(f"Request timed out: {url}") from e
    except httpx.RequestError as e:
        logger.error(f"Network error requesting {e.request.url!r}: {e}", exc_info=True)
        raise PokeAPIConnectionError(f"Network error: {e.request.url!r}") from e
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Resource not found at {e.request.url!r} (404)")
            # Try to determine resource type from endpoint for better error message
            resource_type = endpoint.lstrip('/').split('/')[0] if '/' in endpoint else 'resource'
            identifier = endpoint.lstrip('/').split('/')[-1] if '/' in endpoint else endpoint
            raise ResourceNotFoundError(resource_type, identifier) from e
        else:
            logger.error(f"HTTP error fetching {e.request.url!r}: Status {e.response.status_code}", exc_info=True)
            raise PokeAPIConnectionError(
                f"HTTP error {e.response.status_code} for {e.request.url!r}"
            ) from e
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}", exc_info=True)
        raise # Re-raise other unexpected errors