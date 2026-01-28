"""
utils/tool_cache.py
Cache inteligente para resultados de ferramentas com TTL
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class ToolResultCache:
    """
    Cache inteligente para resultados de ferramentas com TTL.
    
    Características:
    - TTL (Time-To-Live) configurável por entrada
    - Limpeza automática de expirados
    - Thread-safe com locks
    - Hash de argumentos para chaves
    - Sem dependência externa
    """
    
    def __init__(self, default_ttl_minutes: int = 10):
        """
        Inicializa cache
        
        Args:
            default_ttl_minutes: TTL padrão em minutos
        """
        if default_ttl_minutes <= 0:
            raise ValueError("TTL deve ser > 0")
        
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.cache: Dict[str, tuple] = {}  # {key: (resultado, timestamp, ttl)}
        self.lock = Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_stored": 0,
            "expired_cleaned": 0
        }
        
        logger.info(f"ToolResultCache inicializado com TTL padrão: {default_ttl_minutes}m")

    def _make_key(self, tool_name: str, **kwargs) -> str:
        """
        Cria chave hash a partir do nome da ferramenta e argumentos
        
        Args:
            tool_name: Nome da ferramenta
            **kwargs: Argumentos da ferramenta
        
        Returns:
            str: Hash SHA256 da chave
        """
        try:
            payload = json.dumps(
                {"tool": tool_name, "args": kwargs},
                sort_keys=True,
                default=str
            )
            return hashlib.sha256(payload.encode()).hexdigest()
        except Exception as e:
            logger.warning(f"Erro ao gerar chave de cache: {e}")
            return f"fallback_{tool_name}_{id(kwargs)}"

    def get(self, tool_name: str, **kwargs) -> Optional[Any]:
        """
        Recupera resultado em cache se ainda válido
        
        Args:
            tool_name: Nome da ferramenta
            **kwargs: Argumentos da ferramenta
        
        Returns:
            Resultado cacheado ou None se não encontrado/expirado
        
        Exemplo:
            >>> cache = ToolResultCache()
            >>> result = cache.get("SearchTool", query="Python")
            >>> if result is None:
            ...     result = perform_search("Python")
            ...     cache.set("SearchTool", result, query="Python")
        """
        key = self._make_key(tool_name, **kwargs)
        
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                logger.debug(f"Cache miss: {tool_name}")
                return None
            
            result, timestamp, ttl = self.cache[key]
            
            # Verificar se ainda válido
            if datetime.now() - timestamp < ttl:
                self.stats["hits"] += 1
                logger.debug(f"Cache hit: {tool_name}")
                return result
            else:
                # Remover expirado
                del self.cache[key]
                self.stats["misses"] += 1
                logger.debug(f"Cache expirado: {tool_name}")
                return None

    def set(
        self,
        tool_name: str,
        result: Any,
        ttl_minutes: int = None,
        **kwargs
    ) -> bool:
        """
        Armazena resultado em cache
        
        Args:
            tool_name: Nome da ferramenta
            result: Resultado a cachear
            ttl_minutes: TTL em minutos (None = usar padrão)
            **kwargs: Argumentos da ferramenta
        
        Returns:
            bool: True se armazenado com sucesso
        
        Exemplo:
            >>> cache = ToolResultCache()
            >>> cache.set("SearchTool", search_result, ttl_minutes=30, query="Python")
        """
        if result is None:
            logger.warning(f"Tentativa de cachear None para {tool_name}")
            return False
        
        try:
            key = self._make_key(tool_name, **kwargs)
            ttl = timedelta(minutes=ttl_minutes) if ttl_minutes else self.default_ttl
            
            with self.lock:
                self.cache[key] = (result, datetime.now(), ttl)
                self.stats["total_stored"] += 1
                logger.debug(f"Cache set: {tool_name} (TTL: {ttl.total_seconds()}s)")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao armazenar em cache: {e}")
            return False

    def clear(self) -> int:
        """
        Limpa todo o cache
        
        Returns:
            int: Número de entradas removidas
        """
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cache limpo: {count} entradas removidas")
            return count

    def cleanup_expired(self) -> int:
        """
        Remove entradas expiradas
        
        Returns:
            int: Número de entradas expiradas removidas
        """
        now = datetime.now()
        expired_count = 0
        
        with self.lock:
            expired_keys = []
            
            for key, (_, timestamp, ttl) in self.cache.items():
                if now - timestamp >= ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                expired_count += 1
            
            if expired_count > 0:
                self.stats["expired_cleaned"] += expired_count
                logger.debug(f"Limpeza de cache: {expired_count} entradas expiradas removidas")
        
        return expired_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache
        
        Returns:
            Dict com estatísticas
        
        Exemplo:
            >>> cache = ToolResultCache()
            >>> stats = cache.get_stats()
            >>> print(f"Taxa de acerto: {stats['hit_rate']:.2%}")
        """
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (
                self.stats["hits"] / total_requests
                if total_requests > 0
                else 0
            )
            
            return {
                "size": len(self.cache),
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": hit_rate,
                "total_stored": self.stats["total_stored"],
                "expired_cleaned": self.stats["expired_cleaned"],
                "total_requests": total_requests
            }

    def get_detailed_info(self) -> Dict[str, Any]:
        """
        Retorna informações detalhadas do cache incluindo chaves
        
        Returns:
            Dict com informações detalhadas
        """
        with self.lock:
            entries = []
            now = datetime.now()
            
            for key, (result, timestamp, ttl) in self.cache.items():
                age = now - timestamp
                expires_in = ttl - age
                
                entries.append({
                    "key": key[:16] + "...",  # Truncar chave longa
                    "age_seconds": int(age.total_seconds()),
                    "ttl_seconds": int(ttl.total_seconds()),
                    "expires_in_seconds": int(expires_in.total_seconds()),
                    "result_type": type(result).__name__,
                    "expired": expires_in.total_seconds() <= 0
                })
            
            stats = self.get_stats()
            stats["entries"] = entries
            
            return stats

    def __repr__(self) -> str:
        """Representação em string do cache"""
        stats = self.get_stats()
        return (
            f"ToolResultCache(size={stats['size']}, "
            f"hits={stats['hits']}, "
            f"misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate']:.1%})"
        )


# Instância global
_cache: Optional[ToolResultCache] = None


def get_tool_cache(ttl_minutes: int = 10) -> ToolResultCache:
    """
    Factory para obter instância singleton de ToolResultCache
    
    Args:
        ttl_minutes: TTL padrão (ignorado se já inicializado)
    
    Returns:
        ToolResultCache: Instância singleton
    
    Exemplo:
        >>> cache = get_tool_cache()
        >>> result = cache.get("SearchTool", query="Python")
    """
    global _cache
    
    if _cache is None:
        _cache = ToolResultCache(default_ttl_minutes=ttl_minutes)
    
    return _cache


class CacheDecorator:
    """
    Decorator para cachear resultados de funções automaticamente
    
    Exemplo:
        >>> @CacheDecorator(ttl_minutes=30)
        ... def expensive_search(query: str) -> str:
        ...     return perform_search(query)
    """
    
    def __init__(self, ttl_minutes: int = 10):
        """Inicializa decorator com TTL"""
        self.cache = get_tool_cache(ttl_minutes)
        self.ttl = ttl_minutes
    
    def __call__(self, func):
        """Wrap da função"""
        def wrapper(*args, **kwargs):
            # Criar chave a partir do nome da função e argumentos
            key = self.cache._make_key(func.__name__, *args, **kwargs)
            
            # Verificar cache
            result = self.cache.get(func.__name__, *args, **kwargs)
            if result is not None:
                logger.debug(f"Cache hit para {func.__name__}")
                return result
            
            # Executar função
            logger.debug(f"Cache miss para {func.__name__}, executando...")
            result = func(*args, **kwargs)
            
            # Armazenar em cache
            self.cache.set(
                func.__name__,
                result,
                ttl_minutes=self.ttl,
                *args,
                **kwargs
            )
            
            return result
        
        return wrapper


if __name__ == "__main__":
    # Script de teste
    cache = ToolResultCache(default_ttl_minutes=1)
    
    # Testar set/get
    cache.set("TestTool", "result1", query="test")
    result = cache.get("TestTool", query="test")
    print(f"✅ Set/Get: {result == 'result1'}")
    
    # Testar stats
    stats = cache.get_stats()
    print(f"✅ Stats: {stats}")
    print(f"   Hit rate: {stats['hit_rate']:.1%}")
    
    # Testar cleanup
    cache.cleanup_expired()
    print(f"✅ Cleanup: OK")