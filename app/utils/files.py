import json
import logging

logger = logging.getLogger(__name__)

def get_emails(agent=False):
    try:
        with open("app/assets/emails.json", "r", encoding="utf-8") as f:
            emails_list = json.load(f)
            emails_str = json.dumps(emails_list, ensure_ascii=False).replace("{", "{{").replace("}", "}}")
    except:
        emails_str = "[]"

    return emails_str if agent else emails_list

def get_news_countries():
    try:
        with open("app/assets/news.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
        paises = dados.get("countries", [])
        return paises
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON (utils/files.py): {e}")
        return []