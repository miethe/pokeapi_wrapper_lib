# PokeAPI Wrapper Library (Python)

[![PyPI version](https://badge.fury.io/py/pokeapi-wrapper-lib.svg)](https://badge.fury.io/py/pokeapi-wrapper-lib) <!-- Replace with actual PyPI badge if published -->
[![Python package](https://github.com/miethe/pokeapi_wrapper_lib/actions/workflows/python-package.yml/badge.svg)](https://github.com/miethe/pokeapi_wrapper_lib/actions/workflows/python-package.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An asynchronous Python library providing a cleaner interface to interact with the PokeAPI v2 (pokeapi.co). It features:

*   Asynchronous fetching using `httpx`.
*   Optional Redis caching for API responses using `redis-py`.
*   Pydantic models for structured data representation (`BasePokemon`, `BaseSpecies`, etc.).
*   Optional transformation of sprite URLs for local serving.
*   Custom exceptions for better error handling.

## Table of Contents

-   [Features](#features)
-   [Technology Stack](#technology-stack)
-   [Installation](#installation)
-   [Usage](#usage)
    -   [Configuration (Redis)](#configuration-redis)
    -   [Client Management](#client-management)
    -   [Fetching Data](#fetching-data)
    -   [Error Handling](#error-handling)
    -   [Sprite URL Transformation](#sprite-url-transformation)
    -   [Closing Resources](#closing-resources)
-   [Models](#models)
-   [Project Structure](#project-structure)
-   [Running Tests](#running-tests)
-   [Contributing](#contributing)
-   [License](#license)
-   [Acknowledgements](#acknowledgements)

## Features

*   **Async Support:** Built with `asyncio` and `httpx` for non-blocking I/O.
*   **Data Modeling:** Uses Pydantic V2+ to validate and structure data fetched from PokeAPI into Python objects.
*   **Caching:** Optional Redis caching layer to reduce redundant API calls and improve performance.
*   **Error Handling:** Custom exceptions (`ResourceNotFoundError`, `PokeAPIConnectionError`, `CacheError`) for easier error management.
*   **Sprite URL Handling:** Can automatically transform official sprite URLs to point to a local path (configurable via consumer application's settings passed during validation).
*   **Type Hinting:** Fully type-hinted for better developer experience and static analysis.

## Technology Stack

*   Python 3.8+
*   HTTPX (`httpx[http2]>=0.24`)
*   Pydantic (`pydantic>=2.0`)
*   Redis-py (`redis[hiredis]>=4.4`) (Optional, for caching)

## Installation

**From PyPI (Recommended once published):**
```bash
pip install pokeapi-wrapper-lib
```
**From Git:**
```bash
pip install git+https://github.com/miethe/pokeapi_wrapper_lib.git
# Or specific tag/branch:
# pip install git+https://github.com/miethe/pokeapi_wrapper_lib.git@v0.1.0
```

**For Development (Editable install from local clone):**
```bash
# Assuming library repo is cloned locally
pip install -e ./path/to/pokeapi_wrapper_lib
```

## Usage

### Configuration (Redis)

If you want to use caching, configure the Redis connection pool once during your application's startup phase.

```python
import asyncio
import httpx
from pokeapi_lib import configure_redis, close_redis_pool, get_pokemon

async def main():
    # Configure Redis (e.g., using an environment variable)
    # Set decode_responses=True if your cache functions expect strings
    configure_redis(redis_url="redis://localhost:6379/0", decode_responses=True)

    # Create an httpx client (managed by your application)
    async with httpx.AsyncClient() as client:
        # Use the library functions...
        try:
            pokemon = await get_pokemon("pikachu", client=client)
            print(f"Fetched: {pokemon.name}")
        except Exception as e:
            print(f"Error: {e}")

    # Clean up Redis pool on application shutdown
    await close_redis_pool()

if __name__ == "__main__":
    asyncio.run(main())
```

### Client Management

This library requires you to provide an active httpx.AsyncClient instance to its core fetching functions. This allows you to manage the client's lifecycle, configuration (timeouts, limits, proxies), and reuse within your application.

```python
import httpx
from pokeapi_lib import get_pokemon

async def fetch_some_pokemon():
    # It's recommended to reuse the client for multiple requests
    async with httpx.AsyncClient(timeout=10.0) as client: # Example timeout
        try:
            ditto = await get_pokemon("ditto", client=client)
            mew = await get_pokemon(151, client=client)
            print(ditto.name, mew.name)
        except ResourceNotFoundError as e:
            print(f"Could not find: {e}")
        # Handle other PokeAPIErrors...
```

### Fetching Data

Use the exposed async functions:

```python
from pokeapi_lib import get_pokemon, get_species, get_all_generations # etc.

async def get_data(client: httpx.AsyncClient):
    bulbasaur = await get_pokemon(1, client=client)
    print(f"Bulbasaur Base XP: {bulbasaur.base_experience}")
    print(f"Bulbasaur Species URL: {bulbasaur.species.url}") # Access species dict

    bulbasaur_species = await get_species(bulbasaur.id, client=client)
    print(f"Bulbasaur Capture Rate: {bulbasaur_species.capture_rate}")
    print(f"Bulbasaur Evo Chain URL: {bulbasaur_species.evolution_chain['url']}")

    all_gens = await get_all_generations(client=client)
    print(f"Found {len(all_gens)} generations.")
    # Access generation info: all_gens[0].id, all_gens[0].region_name
```

### Error Handling

The library raises specific exceptions:

* ResourceNotFoundError: For 404 errors from PokeAPI.
* PokeAPIConnectionError: For network issues, timeouts, non-404 HTTP errors.
* CacheError: For problems connecting to or interacting with Redis.
* PokeAPIError: Base class for library errors, including data validation failures.

```python
from pokeapi_lib import get_pokemon, ResourceNotFoundError, PokeAPIError

async def safe_fetch(client: httpx.AsyncClient):
    try:
        pokemon = await get_pokemon("nonexistent", client=client)
    except ResourceNotFoundError as e:
        print(f"Caught expected error: {e}")
    except PokeAPIError as e:
        print(f"Caught library error: {e}")
    except Exception as e:
        print(f"Caught unexpected error: {e}")
```

### Sprite URL Transformation

The SpriteData model automatically handles transforming sprite URLs if the consuming application's settings (accessed via pokeapi_lib.config_lib.settings) have sprite_source_mode set to 'local'. The library needs access to this setting during Pydantic validation. (This implies the library either imports a shared config object or receives configuration context).

* Remote Mode (Default): Returns standard https://raw.githubusercontent.com/... URLs (ensured HTTPS).
* Local Mode: Transforms URLs to relative paths like /assets/sprites/sprites/pokemon/1.png based on constants defined (e.g., in config_lib.py).

(Note: The exact mechanism for the library accessing the sprite_source_mode setting needs clarification - ideally, it's passed explicitly during configuration or model validation context rather than relying on a global import from the consuming app's config).

### Closing Resources

Ensure you call close_redis_pool() during your application's shutdown sequence to gracefully close the Redis connection pool managed by the library. The httpx.AsyncClient should be closed by the application that created it (e.g., using an async with block).

### Models

The library provides Pydantic models for key PokeAPI resources:

* NamedAPIResource: Basic { name: str, url: str } structure.
* BasePokemon: Core data from /pokemon/{id}.
* BaseSpecies: Core data from /pokemon-species/{id}.
* GenerationInfo: Data from /generation/{id}.
* TypeInfo: Data from /type/{id}.
* EvolutionChain, ChainLink, EvolutionDetail: Structure for /evolution-chain/{id}.
* SpriteData: Handles sprite URLs and transformation.
* (And various supporting sub-models)

Refer to pokeapi_lib/models.py for detailed field definitions and types.

## Project Structure

<pre>
pokeapi_wrapper_lib/
├── pokeapi_lib/         # Source package
│   ├── __init__.py
│   ├── cache.py
│   ├── client.py
│   ├── config_lib.py    # (Optional) Library-specific config/constants
│   ├── core.py
│   ├── exceptions.py
│   └── models.py
├── tests/               # Unit tests
├── pyproject.toml       # Build config
├── requirements.txt     # Dependencies
└── README.md            # This file
</pre>

## Running Tests
(Add instructions if tests are implemented)

```bash
# Example using pytest
pytest tests/
```

## Contributing

(Standard contribution guidelines - Fork, Branch, Code, Test, PR)

## License

MIT License. See the LICENSE file.

## Acknowledgements

PokeAPI (pokeapi.co): For providing the data API.
