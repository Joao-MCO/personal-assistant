import logging
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

def get_service(credentials=None):
    """
    Constrói o serviço do Google Calendar usando credenciais fornecidas explicitamente.
    """
    # Silencia o aviso sobre discovery_cache (camada extra de segurança)
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

    if not credentials or not credentials.valid:
        # Logamos como WARNING, mas retornamos None para a ferramenta tratar
        logger.warning("Tentativa de criar serviço Google sem credenciais válidas.")
        return None

    try:
        # FIX: cache_discovery=False evita o erro 'file_cache is only supported...'
        # em ambientes de container/cloud como o Streamlit Share.
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)
    except Exception as e:
        logger.error(f"Erro ao construir serviço Google: {e}")
        return None