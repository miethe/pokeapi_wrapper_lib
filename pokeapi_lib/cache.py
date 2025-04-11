# pokeapi_lib/cache.py
import redis.asyncio as redis
import json
import logging
from typing import Optional, Any, Dict
from contextlib import asynccontextmanager
from .exceptions import CacheError

logger = logging.getLogger(__name__)

# --- Cache Management ---
# Allow user to pass pre-configured pool or create one internally

_pool: Optional[redis.ConnectionPool] = None

def configure_redis(redis_url: Optional[str] = None, pool: Optional[redis.ConnectionPool] = None, **kwargs):
    """
    Configures the Redis connection pool for the library.
    Call this once during application startup.

    Args:
        redis_url: The Redis connection URL (e.g., "redis://localhost:6379/0").
                   Ignored if 'pool' is provided.
        pool: An existing redis.asyncio.ConnectionPool instance.
        kwargs: Additional arguments passed to redis.ConnectionPool.from_url
                (e.g., max_connections, decode_responses).
    """
    global _pool
    if pool:
        logger.info("Using provided Redis connection pool.")
        _pool = pool
    elif redis_url:
        logger.info(f"Creating internal Redis connection pool for URL: {redis_url}")
        try:
            # Default decode_responses=True is useful
            kwargs.setdefault('decode_responses', True)
            _pool = redis.ConnectionPool.from_url(redis_url, **kwargs)
        except Exception as e:
            logger.error(f"Failed to create Redis connection pool from URL: {e}", exc_info=True)
            _pool = None # Ensure pool is None on failure
            raise CacheError("Failed to create Redis pool") from e
    else:
        logger.warning("Redis caching disabled: No redis_url or pool provided during configuration.")
        _pool = None

async def close_redis_pool():
    """Closes the internal Redis connection pool if it was created."""
    global _pool
    if _pool:
        try:
            # Use disconnect() for redis-py >= 4.3
            if hasattr(_pool, 'disconnect'):
                 await _pool.disconnect(inuse_connections=True)
            logger.info("Internal Redis connection pool closed.")
        except Exception as e:
            logger.error(f"Error closing Redis pool: {e}", exc_info=True)
        finally:
             _pool = None # Ensure pool is cleared

@asynccontextmanager
async def get_redis_connection() -> redis.Redis:
    """Provides a Redis connection from the configured pool."""
    if _pool is None:
        raise CacheError("Redis pool not configured. Call configure_redis first.")

    conn = None
    try:
        conn = redis.Redis(connection_pool=_pool)
        yield conn
    except redis.RedisError as e:
        logger.error(f"Redis connection error: {e}", exc_info=True)
        raise CacheError("Failed to get Redis connection") from e
    finally:
        # Connection is managed by the pool, explicit close/release usually not needed here
        pass

async def get_cache(key: str) -> Optional[Any]:
    """Retrieves and decodes JSON data from Redis cache."""
    if _pool is None: return None # Cache disabled

    try:
        async with get_redis_connection() as conn:
            cached_data = await conn.get(key)
            if cached_data:
                logger.debug(f"Cache HIT for key: {key}")
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON from cache for key: {key}. Deleting invalid entry.", exc_info=True)
                    # Delete corrupted entry
                    await conn.delete(key)
                    return None
            else:
                logger.debug(f"Cache MISS for key: {key}")
                return None
    except redis.RedisError as e:
        logger.error(f"Redis GET error for key '{key}': {e}", exc_info=True)
        # Optionally raise CacheError or just return None
        return None # Fail gracefully on cache read error

async def set_cache(key: str, value: Any, ttl: int):
    """Stores JSON-serializable data in Redis cache with a TTL."""
    if _pool is None or value is None: return False # Cache disabled or nothing to set

    try:
        json_value = json.dumps(value)
    except (TypeError, OverflowError) as e:
        logger.error(f"Failed to serialize data to JSON for key '{key}': {e}", exc_info=True)
        return False

    try:
        async with get_redis_connection() as conn:
            await conn.setex(key, ttl, json_value)
            logger.debug(f"Cache SET for key: {key} with TTL: {ttl}s")
            return True
    except redis.RedisError as e:
        logger.error(f"Redis SET error for key '{key}': {e}", exc_info=True)
        # Optionally raise CacheError or just return False
        return False # Fail gracefully on cache write error