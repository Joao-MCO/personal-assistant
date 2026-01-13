import logging
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

def get_service(credentials=None):
    """
    Constrói o serviço do Google Calendar usando credenciais fornecidas explicitamente.
    """
    # Silencia o aviso sobre discovery_cache
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

    if not credentials or not credentials.valid:
        logger.warning("get_service chamado sem credenciais válidas.")
        return None

    try:
        return build("calendar", "v3", credentials=credentials)
    except Exception as e:
        logger.error(f"Erro ao construir serviço Google: {e}")
        return None