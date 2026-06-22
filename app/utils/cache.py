import time
import logging
import threading
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class PredictionCache:
    """
    Thread-safe in-memory prediction cache.
    Caches ML prediction responses to prevent redundant executions.
    """
    _cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
    _lock = threading.Lock()

    @classmethod
    def make_key(
        cls,
        lat: float,
        lon: float,
        year: int,
        month: int,
        temp_delta: float = 0.0,
        rain_delta: float = 0.0,
        sm_delta: float = 0.0,
        evap_delta: float = 0.0,
        ro_delta: float = 0.0
    ) -> str:
        """Generates a unique cache key based on coordinates, date, and scenario parameters."""
        # Round coordinates to 4 decimal places to prevent floating point differences
        scenario_hash = f"t_{temp_delta:.4f}_r_{rain_delta:.4f}_sm_{sm_delta:.4f}_evap_{evap_delta:.4f}_ro_{ro_delta:.4f}"
        return f"{lat:.4f}_{lon:.4f}_{year}_{month}_{scenario_hash}"

    @classmethod
    def get(cls, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a cached value if it exists and has not expired."""
        with cls._lock:
            if key not in cls._cache:
                return None
            
            val, expiry = cls._cache[key]
            if time.time() > expiry:
                # Evict expired entry
                del cls._cache[key]
                logger.debug(f"Cache expired for key: {key}")
                return None
                
            logger.info(f"Cache HIT for key: {key}")
            return val

    @classmethod
    def set(cls, key: str, value: Dict[str, Any], ttl: int = 86400) -> None:
        """Stores a value in the cache with a specified Time-to-Live (in seconds)."""
        with cls._lock:
            expiry = time.time() + ttl
            cls._cache[key] = (value, expiry)
            logger.debug(f"Cache SET for key: {key} (TTL: {ttl}s)")

    @classmethod
    def clear(cls) -> None:
        """Clears the entire cache."""
        with cls._lock:
            cls._cache.clear()
            logger.info("Prediction Cache cleared successfully.")
            
    @classmethod
    def get_prediction(cls, key: str, pred_type: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific prediction type (e.g. temperature) from the cached entry."""
        data = cls.get(key)
        if data:
            return data.get(pred_type)
        return None

    @classmethod
    def set_prediction(cls, key: str, pred_type: str, pred_value: Dict[str, Any], ttl: int = 86400) -> None:
        """Stores a specific prediction type under a key, merging with existing data if present."""
        with cls._lock:
            expiry = time.time() + ttl
            if key in cls._cache:
                cls._cache[key][0][pred_type] = pred_value
                # Keep original expiry or update it? Let's keep the original or update it to extend.
                cls._cache[key] = (cls._cache[key][0], expiry)
            else:
                cls._cache[key] = ({pred_type: pred_value}, expiry)
            logger.debug(f"Cache SET for key: {key}, type: {pred_type} (TTL: {ttl}s)")

    @classmethod
    def get_size(cls) -> int:
        """Returns the number of entries currently in the cache."""
        with cls._lock:
            return len(cls._cache)
