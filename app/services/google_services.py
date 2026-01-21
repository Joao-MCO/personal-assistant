import logging
import time
import random
import httplib2
from threading import Lock
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from google_auth_httplib2 import AuthorizedHttp

logger = logging.getLogger(__name__)

_REFRESH_LOCK = Lock()

# --------------------------------------------------------

def _safe_refresh(credentials):
    if credentials and credentials.expired and credentials.refresh_token:
        with _REFRESH_LOCK:
            if credentials.expired:
                credentials.refresh(Request())

# --------------------------------------------------------

def _with_retry(fn, max_retries=3, base_delay=0.5):
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except HttpError as e:
            status = getattr(e.resp, "status", None)
            if status and status < 500:
                raise  # erro lógico → não retry
        except Exception as e:
            if attempt == max_retries:
                raise

        sleep = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.3)
        logger.warning(f"Retry {attempt}/{max_retries} em {sleep:.2f}s")
        time.sleep(sleep)

# --------------------------------------------------------

def _build_service(credentials, service_name, version):
    def factory():
        _safe_refresh(credentials)
        http = httplib2.Http(timeout=30)
        authed_http = AuthorizedHttp(credentials, http=http)
        return build(
            service_name,
            version,
            http=authed_http,
            cache_discovery=False
        )

    try:
        return _with_retry(factory)
    except Exception as e:
        logger.error(f"Erro ao criar serviço {service_name}: {e}", exc_info=True)
        return None

# --------------------------------------------------------

def get_service(credentials=None, service="calendar"):
    if not credentials or not credentials.valid:
        return None

    if service == "calendar":
        return _build_service(credentials, "calendar", "v3")

    if service == "gmail":
        return _build_service(credentials, "gmail", "v1")

    return None
