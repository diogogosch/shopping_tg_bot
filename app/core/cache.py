import redis
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to in-memory cache")
            self.redis_client = None
            self._memory_cache = {}
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            return pickle.dumps(value)
    
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            return json.loads(value.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return pickle.loads(value)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value is not None:
                    return self._deserialize(value)
            else:
                return self._memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """Set value in cache"""
        try:
            if ttl is None:
                ttl = settings.redis_ttl
            
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            if self.redis_client:
                serialized_value = self._serialize(value)
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                self._memory_cache[key] = value
                return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                return self._memory_cache.pop(key, None) is not None
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def get_user_cache_key(self, user_id: int, suffix: str) -> str:
        """Generate user-specific cache key"""
        return f"user:{user_id}:{suffix}"
    
    def cache_user_suggestions(self, user_id: int, suggestions: list, ttl: int = 1800):
        """Cache AI suggestions for user"""
        key = self.get_user_cache_key(user_id, "suggestions")
        return self.set(key, suggestions, ttl)
    
    def get_user_suggestions(self, user_id: int) -> Optional[list]:
        """Get cached AI suggestions for user"""
        key = self.get_user_cache_key(user_id, "suggestions")
        return self.get(key)

cache = CacheService()
