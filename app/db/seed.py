"""
Seeds executadas uma vez no startup (ver db/base.py:init_db). Ambas são
idempotentes -- só fazem algo se a tabela de destino estiver vazia -- então
não sobrescrevem dados que você já tenha editado depois da primeira subida.
"""

import hashlib
import logging

from sqlalchemy.orm import Session as DBSession

from db.models import ApiClient, Employee
from utils.files import get_employees_from_json
from settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)


def seed_employees_from_json(db: DBSession) -> None:
    """
    Popula `employees` a partir de app/assets/emails.json na primeira subida.
    Depois disso, a tabela é a fonte da verdade -- o JSON não é mais
    consultado em tempo de execução (só nesta seed).
    """
    if db.query(Employee).first() is not None:
        return

    emails = get_employees_from_json()
    for item in emails:
        nome = (item.get("nome") or "").strip()
        email = (item.get("email") or "").strip()
        if not email:
            continue
        db.add(Employee(nome=nome, email=email, ativo=True))
    db.commit()
    logger.info(f"Seed: {len(emails)} funcionário(s) carregado(s) de emails.json para a tabela employees.")


def seed_legacy_api_key(db: DBSession) -> None:
    """
    Se API_KEY (o mecanismo antigo, de chave única) estiver configurada e a
    tabela api_clients ainda estiver vazia, cria um cliente "legacy" com essa
    chave -- assim quem já tinha API_KEY configurada não perde acesso ao
    migrar para o sistema multi-cliente baseado em api_clients.
    """
    if not Settings.api_key:
        return
    if db.query(ApiClient).first() is not None:
        return

    key_hash = hashlib.sha256(Settings.api_key.encode()).hexdigest()
    db.add(ApiClient(name="legacy (API_KEY do .env)", key_hash=key_hash, active=True))
    db.commit()
    logger.info("Seed: API_KEY legado migrado para a tabela api_clients como cliente 'legacy'.")