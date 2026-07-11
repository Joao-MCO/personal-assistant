"""
Redirect do Encurtador de URL. Fora do namespace /chat de propósito -- é um
link que vai parar no navegador de qualquer pessoa (não só quem conversa com
a Cidinha), então não passa por verify_api_key nem por autenticação alguma,
igual às rotas de OAuth.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from db.base import SessionLocal
from db.models import ShortUrl

logger = logging.getLogger(__name__)
router = APIRouter(tags=["shorturl"])


@router.get("/s/{slug}")
async def redirect_short_url(slug: str):
    db = SessionLocal()
    try:
        row = db.query(ShortUrl).filter(ShortUrl.slug == slug).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Link não encontrado.")
        row.clicks += 1
        original_url = row.original_url
        db.commit()
    finally:
        db.close()

    return RedirectResponse(original_url)