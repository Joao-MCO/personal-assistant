import logging
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class SecureCredentialStorage:
    """
    Armazenamento seguro de credenciais com criptografia Fernet.
    
    Características:
    - Criptografia end-to-end com Fernet
    - Armazenamento em memória
    - TTL automático
    - Thread-safe
    - Sem dependências externas (apenas cryptography)
    """
    
    def __init__(
        self,
        encryption_key: str = None,
        ttl_hours: int = 1
    ):
        """
        Inicializa storage seguro
        
        Args:
            encryption_key: Chave Fernet (padrão: env var ENCRYPTION_KEY)
            ttl_hours: TTL em horas (padrão: 1)
        
        Raises:
            RuntimeError: Se chave de criptografia não estiver configurada
        """
        # Configurar criptografia
        self.encryption_key = encryption_key or os.environ.get('ENCRYPTION_KEY')
        if not self.encryption_key:
            raise RuntimeError(
                "ENCRYPTION_KEY não configurada. "
                "Execute: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        
        try:
            self.cipher = Fernet(self.encryption_key.encode())
            logger.info("✅ Criptografia Fernet inicializada")
        except Exception as e:
            raise RuntimeError(f"Chave de criptografia inválida: {e}")
        
        self.ttl = timedelta(hours=ttl_hours)
        self.storage: Dict[str, tuple] = {}  # {key: (encrypted_data, timestamp, ttl)}
        
        logger.info(f"✅ SecureCredentialStorage inicializado (TTL: {ttl_hours}h)")

    def _make_key(self, user_id: str) -> str:
        """Cria chave para credencial"""
        return f"creds:{user_id}"

    def _cleanup_expired(self) -> int:
        """Remove credenciais expiradas"""
        now = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp, ttl) in self.storage.items():
            if now - timestamp >= ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.storage[key]
        
        return len(expired_keys)

    def store_credentials(
        self,
        user_id: str,
        credentials: Any
    ) -> bool:
        """
        Armazena credenciais de forma segura
        
        Args:
            user_id: ID único do usuário (email)
            credentials: Objeto de credenciais Google
        
        Returns:
            bool: True se sucesso, False se falha
        """
        if not user_id:
            logger.error("user_id é obrigatório")
            return False
        
        try:
            # Extrair apenas dados públicos (NUNCA client_secret)
            data = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "scopes": credentials.scopes,
            }
            
            # Validar que temos dados essenciais
            if not data["token"] or not data["refresh_token"]:
                logger.error("Token ou refresh_token ausentes")
                return False
            
            # Serializar para JSON
            json_str = json.dumps(data, default=str)
            
            # Criptografar
            encrypted = self.cipher.encrypt(json_str.encode())
            
            # Armazenar em memória
            key = self._make_key(user_id)
            self.storage[key] = (
                encrypted.decode(),
                datetime.now(),
                self.ttl
            )
            
            logger.info(f"✅ Credenciais armazenadas para {user_id}")
            return True
        
        except AttributeError as e:
            logger.error(f"Credencial com formato inválido: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao armazenar credenciais: {e}", exc_info=True)
            return False

    def get_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera credenciais descriptografadas
        
        Args:
            user_id: ID único do usuário
        
        Returns:
            Dict com credenciais ou None se não encontrado/inválido
        """
        if not user_id:
            logger.error("user_id é obrigatório")
            return None
        
        try:
            # Limpar expirados periodicamente
            self._cleanup_expired()
            
            key = self._make_key(user_id)
            
            if key not in self.storage:
                logger.debug(f"Credenciais não encontradas para {user_id}")
                return None
            
            encrypted_data, timestamp, ttl = self.storage[key]
            
            # Verificar se expirou
            if datetime.now() - timestamp >= ttl:
                del self.storage[key]
                logger.debug(f"Credenciais expiradas para {user_id}")
                return None
            
            # Descriptografar
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            credentials_data = json.loads(decrypted)
            
            logger.debug(f"✅ Credenciais recuperadas para {user_id}")
            return credentials_data
        
        except InvalidToken as e:
            logger.error(f"Erro de descriptografia: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao recuperar credenciais: {e}", exc_info=True)
            return None

    def delete_credentials(self, user_id: str) -> bool:
        """
        Deleta credenciais (logout)
        
        Args:
            user_id: ID único do usuário
        
        Returns:
            bool: True se sucesso
        """
        if not user_id:
            logger.error("user_id é obrigatório")
            return False
        
        try:
            key = self._make_key(user_id)
            
            if key in self.storage:
                del self.storage[key]
            
            logger.info(f"✅ Credenciais deletadas para {user_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar credenciais: {e}")
            return False

    def credential_exists(self, user_id: str) -> bool:
        """
        Verifica se credencial existe e é válida
        
        Args:
            user_id: ID único do usuário
        
        Returns:
            bool: True se existe e válida
        """
        if not user_id:
            return False
        
        try:
            key = self._make_key(user_id)
            
            if key not in self.storage:
                return False
            
            encrypted_data, timestamp, ttl = self.storage[key]
            
            # Verificar expiração
            if datetime.now() - timestamp >= ttl:
                del self.storage[key]
                return False
            
            # Tentar descriptografar para validar
            try:
                self.cipher.decrypt(encrypted_data.encode())
                return True
            except InvalidToken:
                logger.warning(f"Credencial inválida para {user_id}")
                return False
        
        except Exception as e:
            logger.error(f"Erro ao verificar existência: {e}")
            return False

    def get_storage_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do storage"""
        self._cleanup_expired()
        
        return {
            "credentials_stored": len(self.storage),
            "ttl_hours": self.ttl.total_seconds() / 3600,
            "storage_type": "memory",
            "requires_redis": False
        }


# Singleton para uso em toda aplicação
_credential_storage = None


def get_credential_storage(**kwargs) -> SecureCredentialStorage:
    """
    Factory para obter instância singleton de SecureCredentialStorage
    
    Args:
        **kwargs: Argumentos para SecureCredentialStorage
    
    Returns:
        SecureCredentialStorage: Instância singleton
    
    Raises:
        RuntimeError: Se configuração inválida
    """
    global _credential_storage
    if _credential_storage is None:
        try:
            _credential_storage = SecureCredentialStorage(**kwargs)
        except RuntimeError as e:
            logger.critical(f"Falha ao inicializar SecureCredentialStorage: {e}")
            raise
    return _credential_storage