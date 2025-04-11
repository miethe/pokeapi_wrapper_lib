# pokeapi_lib/exceptions.py

class PokeAPIError(Exception):
    """Base exception for errors related to the PokeAPI wrapper."""
    pass

class ResourceNotFoundError(PokeAPIError):
    """Raised when a requested resource (Pokemon, Move, etc.) is not found."""
    def __init__(self, resource_type: str, identifier: str | int):
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"{resource_type.capitalize()} '{identifier}' not found in PokeAPI.")

class PokeAPIConnectionError(PokeAPIError):
    """Raised when there's an issue connecting to PokeAPI."""
    pass

class CacheError(PokeAPIError):
     """Raised for cache specific errors."""
     pass