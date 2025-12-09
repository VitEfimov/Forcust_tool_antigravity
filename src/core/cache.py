"""
Time-based caching decorator.
Cache refreshes at specific hours (e.g., 10am, 12pm, 2pm, 4pm EST).
"""
import functools
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import hashlib
import json

# In-memory cache store
_cache: Dict[str, Dict[str, Any]] = {}

def _get_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a unique cache key from function name and arguments."""
    key_parts = [func_name]
    for arg in args:
        try:
            key_parts.append(str(arg))
        except:
            key_parts.append(repr(arg))
    for k, v in sorted(kwargs.items()):
        try:
            key_parts.append(f"{k}={v}")
        except:
            key_parts.append(f"{k}={repr(v)}")
    return hashlib.md5(":".join(key_parts).encode()).hexdigest()

def _get_current_cache_window(refresh_hours: List[int]) -> str:
    """
    Determine current cache window based on refresh hours.
    Returns a string like '2025-12-05_10' representing today + valid cache hour.
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_hour = now.hour
    
    # Find the most recent refresh hour that has passed
    valid_hour = None
    for h in sorted(refresh_hours):
        if current_hour >= h:
            valid_hour = h
        else:
            break
    
    # If current time is before first refresh hour, use previous day's last hour
    if valid_hour is None:
        yesterday = (now.replace(hour=0, minute=0, second=0) - 
                     __import__('datetime').timedelta(days=1))
        today = yesterday.strftime("%Y-%m-%d")
        valid_hour = max(refresh_hours)
    
    return f"{today}_{valid_hour}"

def timed_cache(refresh_hours: List[int] = [10, 12, 14, 16]):
    """
    Decorator that caches function results until the next scheduled refresh time.
    
    Args:
        refresh_hours: List of hours (24h format) when cache should refresh.
                       Default: 10am, 12pm, 2pm, 4pm
    
    Usage:
        @timed_cache(refresh_hours=[10, 12, 14, 16])
        def expensive_function(symbol):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = _get_cache_key(func.__name__, args, kwargs)
            cache_window = _get_current_cache_window(refresh_hours)
            
            # Check if we have valid cached data
            if cache_key in _cache:
                cached = _cache[cache_key]
                if cached.get('window') == cache_window:
                    print(f"[CACHE HIT] {func.__name__} - window: {cache_window}")
                    return cached['data']
            
            # Cache miss - call function and store result
            print(f"[CACHE MISS] {func.__name__} - computing fresh data")
            result = func(*args, **kwargs)
            
            _cache[cache_key] = {
                'window': cache_window,
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
        return wrapper
    return decorator

def clear_cache(func_name: Optional[str] = None):
    """
    Clear cache entries.
    
    Args:
        func_name: If provided, clear only entries for this function.
                   If None, clear entire cache.
    """
    global _cache
    if func_name is None:
        _cache = {}
        print("[CACHE] Cleared all cache entries")
    else:
        keys_to_remove = [k for k in _cache.keys() if k.startswith(func_name)]
        for k in keys_to_remove:
            del _cache[k]
        print(f"[CACHE] Cleared entries for {func_name}")

def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about current cache state."""
    return {
        "total_entries": len(_cache),
        "entries": {k: {"window": v["window"], "timestamp": v["timestamp"]} 
                    for k, v in _cache.items()}
    }
