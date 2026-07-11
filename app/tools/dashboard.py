"""
Encurtador de URL self-hosted (não depende de Bitly/TinyURL) -- o redirect
de fato acontece em app/api/shorturl.py (GET /s/{slug}), fora do /chat.
"""

import logging
import secrets
import string
import time
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, PrivateAttr

from db.base import SessionLocal
from db.models import ShortUrl
from models.tools import EncurtarURLInput
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

_ALFABETO_SLUG = string.ascii_lowercase + string.digits


def _gerar_slug(tamanho: int = 6) -> str:
    return "".join(secrets.choice(_ALFABETO_SLUG) for _ in range(tamanho))


class EncurtarURL(BaseTool):
    name: str = "EncurtarURL"
    description: str = "Use para encurtar uma URL longa em um link curto."
    args_schema: Type[BaseModel] = EncurtarURLInput
    return_direct: bool = False
    _employee_id: Optional[int] = PrivateAttr(default=None)

    def set_employee_id(self, employee_id: Optional[int]):
        self._employee_id = employee_id

    def _run(self, url: str, slug_personalizado: Optional[str] = None) -> str:
        start = time.time()
        if not (url.startswith("http://") or url.startswith("https://")):
            return f"'{url}' não parece ser uma URL válida (precisa começar com http:// ou https://)."

        db = SessionLocal()
        try:
            if slug_personalizado:
                if db.query(ShortUrl).filter(ShortUrl.slug == slug_personalizado).first():
                    return f"O slug '{slug_personalizado}' já está em uso — escolha outro."
                slug = slug_personalizado
            else:
                slug = _gerar_slug()
                while db.query(ShortUrl).filter(ShortUrl.slug == slug).first():
                    slug = _gerar_slug()

            db.add(ShortUrl(slug=slug, original_url=url, employee_id=self._employee_id))
            db.commit()
        finally:
            db.close()
            logger.info(f"EncurtarURL — tempo de execução: {time.time() - start:.2f}s")

        base = Settings.public_base_url or "(configure PUBLIC_BASE_URL)"
        return f"Link encurtado: {base}/s/{slug}"