import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Caminho absoluto da pasta "app/assets", calculado a partir deste arquivo
# (utils/ -> app/ -> assets/). Isso evita depender do diretório de onde o
# processo é iniciado (necessário agora que a aplicação roda via uvicorn,
# e não mais via `streamlit run app/main.py` a partir da raiz do projeto).
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def get_emails(agent=False):
    emails_list = []
    try:
        with open(ASSETS_DIR / "emails.json", "r", encoding="utf-8") as f:
            emails_list = json.load(f)
            emails_str = json.dumps(emails_list, ensure_ascii=False).replace("{", "{{").replace("}", "}}")
    except Exception as e:
        logger.error(f"Erro ao carregar emails.json (utils/files.py): {e}")
        emails_str = "[]"

    return emails_str if agent else emails_list