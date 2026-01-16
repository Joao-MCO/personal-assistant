import logging
import streamlit as st
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

@st.cache_resource(ttl=3600)
def get_cached_service(_credentials, service_name, service_version):
    """
    Cria e cacheia o serviço do Google.
    O underscore em _credentials diz ao Streamlit para não tentar fazer hash desse objeto complexo.
    """
    try:
        # cache_discovery=False é vital para ambientes cloud/docker
        return build(service_name, service_version, credentials=_credentials, cache_discovery=False)
    except Exception as e:
        logger.error(f"Erro ao construir serviço {service_name}: {e}")
        return None

def get_service(credentials=None, service="calendar"):
    if not credentials or not credentials.valid:
        logger.warning("Credenciais inválidas ou ausentes.")
        return None

    if service == "calendar":
        return get_cached_service(credentials, "calendar", "v3")
    elif service == "gmail":
        return get_cached_service(credentials, "gmail", "v1")
    
    return None