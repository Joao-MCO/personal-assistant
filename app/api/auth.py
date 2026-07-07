"""
Autenticação da API — dois mecanismos independentes:

1. `verify_api_key` (dependency): protege /chat e /chat/{id}/history com uma
   chave fixa simples (header X-API-Key). Responde "quem pode chamar a API".
   Pensado para uso interno da SharkDev, não para múltiplos usuários finais
   com permissões diferentes — se isso vier a ser necessário, é o ponto certo
   para evoluir para JWT por usuário.

2. As rotas /auth/google/* abaixo: fluxo OAuth do Google (Calendar/Gmail),
   portado do antigo `MemoryGoogleAuth` do main.py, agora guardando as
   credenciais no SessionStore (servidor) em vez de st.session_state
   (navegador). Responde "quais dados do Google essa sessão pode acessar".

Essas rotas de login/callback são acessadas via redirecionamento do próprio
navegador (o usuário clica num link, o Google redireciona de volta) — por
isso elas NÃO passam por verify_api_key: um navegador navegando via link não
tem como anexar um header customizado. A proteção real desse fluxo é o
próprio `state` (amarrado à sessão) e o consentimento na tela do Google.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session as DBSession

from api.schemas import GoogleStatusResponse
from db.base import get_db
from db.models import ApiClient
from services.session_store import session_store
from utils.files import get_emails
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = "X-API-Key"

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.readonly",
]


async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias=API_KEY_HEADER),
    db: DBSession = Depends(get_db),
):
    """
    Dependency do FastAPI usada nas rotas de /chat. Cada chave é guardada só
    como hash (sha256) na tabela `api_clients` -- o texto puro só existe no
    momento em que é gerado, em POST /admin/api-clients, e não é recuperável
    depois disso.

    Se a tabela estiver vazia (nenhum cliente cadastrado e nenhuma API_KEY
    legada configurada no .env), a verificação fica desabilitada -- mesmo
    comportamento "modo dev" que já existia antes desta migração para SQL.
    """
    if db.query(ApiClient).count() == 0:
        return

    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key ausente.")

    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    client = (
        db.query(ApiClient)
        .filter(ApiClient.key_hash == key_hash, ApiClient.active == True)  # noqa: E712
        .first()
    )
    if client is None:
        raise HTTPException(status_code=401, detail="X-API-Key inválida, revogada ou ausente.")

    client.last_used_at = datetime.now(timezone.utc)
    db.commit()


router = APIRouter(prefix="/auth/google", tags=["auth"])


def _load_client_config() -> dict:
    raw = Settings.google.get("client_secret")
    if not raw:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_SECRET não configurado no servidor."
        )
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_SECRET não é um JSON válido."
        )


def _get_flow() -> Flow:
    return Flow.from_client_config(
        _load_client_config(),
        scopes=SCOPES,
        redirect_uri=Settings.auth["redirect_uri"],
    )


@router.get("/login")
async def google_login(session_id: Optional[str] = Query(default=None)):
    """
    Inicia o login Google: redireciona o navegador para a tela de consentimento.
    Passe seu `session_id` (se já tiver um de uma conversa em andamento) para
    que as credenciais sejam associadas a ela; caso contrário, uma nova sessão
    é criada e devolvida ao final do fluxo, em /auth/google/callback.
    """
    sid = session_store.get_or_create(session_id)
    flow = _get_flow()
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=sid,
    )
    return RedirectResponse(authorization_url)


@router.get("/callback")
async def google_callback(code: str, state: str):
    """Endpoint de retorno chamado pelo próprio Google após o consentimento."""
    sid = state
    try:
        flow = _get_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
    except Exception:
        logger.exception("Erro ao trocar 'code' por token no fluxo OAuth do Google")
        raise HTTPException(status_code=400, detail="Falha na autenticação com o Google.")

    creds_dict = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    session_store.set_google_credentials(sid, creds_dict)

    user_info = {}
    try:
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            email = data.get("email")
            nome_user = data.get("name", "Usuário")

            # Tenta trocar pelo nome amigável da lista interna da SharkDev
            try:
                emails_internos = get_emails()
                match = next((x for x in emails_internos if x.get("email") == email), None)
                if match:
                    nome_user = match["nome"].replace(" - SharkDev", "")
            except Exception:
                logger.warning("Não foi possível casar o e-mail com a lista interna.", exc_info=True)

            user_info = {"user": nome_user, "email": email}
            session_store.set_user_info(sid, user_info)
    except Exception:
        logger.exception("Erro ao buscar userinfo do Google")

    return {
        "session_id": sid,
        "connected": True,
        "user_info": user_info,
        "message": (
            "Login realizado com sucesso. Envie este session_id nas próximas "
            "chamadas a /chat para manter acesso à Agenda e ao Gmail."
        ),
    }


@router.get("/status", response_model=GoogleStatusResponse)
async def google_status(session_id: str = Query(...)):
    """Verifica se a sessão informada está autenticada no Google."""
    creds_dict = session_store.get_google_credentials(session_id)
    user_info = session_store.get_user_info(session_id) or {}
    return GoogleStatusResponse(
        session_id=session_id,
        connected=bool(creds_dict),
        email=user_info.get("email"),
        name=user_info.get("user"),
    )


@router.post("/logout")
async def google_logout(session_id: str = Query(...)):
    """Remove as credenciais Google da sessão (mantém o histórico de conversa)."""
    session_store.set_google_credentials(session_id, None)
    session_store.set_user_info(session_id, None)
    return {"session_id": session_id, "connected": False}