import logging
from typing import Optional, Any
from google.auth.transport.requests import Request
import google.oauth2.credentials

logger = logging.getLogger(__name__)


class GoogleCredentialManager:
    """
    Gerencia credenciais Google com refresh automático de tokens
    
    Características:
    - Refresh automático quando token expira
    - Validação de credenciais
    - Tratamento seguro de erros
    """
    
    @staticmethod
    def ensure_valid_credentials(
        credentials: google.oauth2.credentials.Credentials
    ) -> bool:
        """
        Verifica e refresh credenciais se necessário
        
        Args:
            credentials: Credenciais OAuth2 do Google
        
        Returns:
            bool: True se credenciais são válidas após operação
        
        Exemplo:
            >>> if GoogleCredentialManager.ensure_valid_credentials(creds):
            ...     service = build('gmail', 'v1', credentials=creds)
            ... else:
            ...     st.error("Credenciais inválidas. Faça login novamente.")
        """
        if not credentials:
            logger.warning("Credenciais None fornecidas")
            return False
        
        try:
            # Se token expirou e temos refresh token
            if credentials.expired and credentials.refresh_token:
                logger.info("Token expirado, tentando refresh...")
                try:
                    credentials.refresh(Request())
                    logger.info("✅ Token renovado com sucesso")
                    return True
                except Exception as refresh_error:
                    logger.error(f"Erro ao renovar token: {refresh_error}")
                    return False
            
            # Se ainda válido
            elif credentials.valid:
                logger.debug("Token ainda válido")
                return True
            
            # Se não tem refresh token e está inválido
            else:
                logger.warning(
                    "Credenciais inválidas e sem refresh token. "
                    "Faça login novamente."
                )
                return False
        
        except AttributeError as e:
            logger.error(f"Formato de credencial inválido: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao validar credenciais: {e}")
            return False

    @staticmethod
    def get_service(
        credentials: google.oauth2.credentials.Credentials,
        service_name: str = "gmail"
    ) -> Optional[Any]:
        """
        Obtém serviço Google com refresh automático de credenciais
        
        Args:
            credentials: Credenciais OAuth2
            service_name: Nome do serviço ('gmail', 'calendar', etc)
        
        Returns:
            Service do Google API ou None se falha
        
        Exemplo:
            >>> service = GoogleCredentialManager.get_service(creds, 'gmail')
            >>> if service:
            ...     results = service.users().messages().list(userId='me').execute()
        """
        if not credentials:
            logger.error("Credenciais não fornecidas")
            return None
        
        try:
            # Validar e refresh se necessário
            if not GoogleCredentialManager.ensure_valid_credentials(credentials):
                logger.error(f"Credenciais inválidas para {service_name}")
                return None
            
            # Importar aqui para evitar circular imports
            from googleapiclient.discovery import build
            
            logger.info(f"Criando serviço {service_name}...")
            service = build(service_name, 'v1', credentials=credentials)
            
            logger.info(f"✅ Serviço {service_name} criado com sucesso")
            return service
        
        except ImportError as e:
            logger.error(f"googleapiclient não instalado: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Erro ao criar serviço {service_name}: {e}",
                exc_info=True
            )
            return None

    @staticmethod
    def is_credentials_valid(
        credentials: google.oauth2.credentials.Credentials
    ) -> bool:
        """
        Verifica se credenciais são válidas (sem refresh)
        
        Args:
            credentials: Credenciais a verificar
        
        Returns:
            bool: True se válidas
        """
        if not credentials:
            return False
        
        try:
            return credentials.valid
        except Exception as e:
            logger.error(f"Erro ao verificar validade de credenciais: {e}")
            return False

    @staticmethod
    def is_credentials_expired(
        credentials: google.oauth2.credentials.Credentials
    ) -> bool:
        """
        Verifica se credenciais estão expiradas
        
        Args:
            credentials: Credenciais a verificar
        
        Returns:
            bool: True se expiradas
        """
        if not credentials:
            return True
        
        try:
            return credentials.expired
        except Exception as e:
            logger.error(f"Erro ao verificar expiração: {e}")
            return True

    @staticmethod
    def get_credentials_info(
        credentials: google.oauth2.credentials.Credentials
    ) -> dict:
        """
        Retorna informações sobre credenciais
        
        Args:
            credentials: Credenciais a analisar
        
        Returns:
            Dict com informações
        """
        if not credentials:
            return {"error": "Credenciais não fornecidas"}
        
        try:
            return {
                "valid": credentials.valid,
                "expired": credentials.expired,
                "has_refresh_token": bool(credentials.refresh_token),
                "token_uri": credentials.token_uri,
                "scopes": credentials.scopes
            }
        except Exception as e:
            logger.error(f"Erro ao obter informações: {e}")
            return {"error": str(e)}


# Factory para serviços Google
class GoogleServiceFactory:
    """Factory para criar serviços Google com gerenciamento de credenciais"""
    
    _services_cache = {}
    
    @staticmethod
    def get_gmail_service(
        credentials: google.oauth2.credentials.Credentials
    ) -> Optional[Any]:
        """Obtém serviço Gmail com credenciais válidas"""
        return GoogleCredentialManager.get_service(credentials, "gmail")
    
    @staticmethod
    def get_calendar_service(
        credentials: google.oauth2.credentials.Credentials
    ) -> Optional[Any]:
        """Obtém serviço Calendar com credenciais válidas"""
        return GoogleCredentialManager.get_service(credentials, "calendar")
    
    @staticmethod
    def get_drive_service(
        credentials: google.oauth2.credentials.Credentials
    ) -> Optional[Any]:
        """Obtém serviço Drive com credenciais válidas"""
        return GoogleCredentialManager.get_service(credentials, "drive")
    
    @staticmethod
    def get_service(
        credentials: google.oauth2.credentials.Credentials,
        service_name: str
    ) -> Optional[Any]:
        """Obtém qualquer serviço Google com credenciais válidas"""
        return GoogleCredentialManager.get_service(credentials, service_name)


if __name__ == "__main__":
    # Script de teste
    print("GoogleCredentialManager - Teste de disponibilidade")
    print("=" * 60)
    
    # Simular credenciais (não funcional)
    print("✅ Módulo carregado com sucesso")
    print("Funções disponíveis:")
    print("  - ensure_valid_credentials(credentials)")
    print("  - get_service(credentials, service_name)")
    print("  - is_credentials_valid(credentials)")
    print("  - is_credentials_expired(credentials)")
    print("  - get_credentials_info(credentials)")