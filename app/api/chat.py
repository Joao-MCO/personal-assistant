"""
Rotas de conversa com a Cidinha.

O endpoint /chat aceita multipart/form-data (e não JSON puro) porque precisa
suportar anexos opcionais no mesmo request — é o equivalente ao popover de
upload que existia ao lado do chat_input no Streamlit. Texto e arquivos viajam
juntos, exatamente como antes.

Notamos que cada chamada cria uma AgentFactory nova (em vez de reaproveitar
uma por sessão). Isso é deliberado: as tools de Calendar/Gmail guardam as
credenciais do usuário como estado da própria instância (`tool.set_credentials`),
então uma AgentFactory compartilhada entre sessões/usuários correria o risco de
uma requisição ler as credenciais de outra. Criar uma instância nova por
chamada custa pouco (é só montar o grafo e vincular as tools) e elimina esse
risco por completo. Se isso um dia pesar em volume alto de requisições, dá para
otimizar reaproveitando uma factory por sessão — mas exigiria revisar as tools
para não guardarem credenciais como atributo de instância.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
import google.oauth2.credentials

from agent.agent import AgentFactory
from api.auth import verify_api_key
from api.schemas import ChatMessage, ChatResponse, HistoryResponse
from services.session_store import session_store
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def _build_credentials(creds_dict: Optional[dict]) -> Optional[google.oauth2.credentials.Credentials]:
    if not creds_dict:
        return None
    return google.oauth2.credentials.Credentials(**creds_dict)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    message: str = Form(..., description="Mensagem do usuário para a Cidinha."),
    session_id: Optional[str] = Form(
        default=None,
        description="session_id de uma conversa em andamento. Omita para iniciar uma nova."
    ),
    llm: str = Form(
        default=Settings.orchestrator,
        description="Modelo: 'gemini' (padrão, configurável via ORCHESTRATOR_MODEL), 'gpt' ou 'claude'."
    ),
    files: List[UploadFile] = File(default=[]),
    _api_key: None = Depends(verify_api_key),
):
    sid = session_store.get_or_create(session_id)

    files_to_send = []
    for f in files:
        content = await f.read()
        files_to_send.append({
            "name": f.filename,
            "data": content,
            "mime": f.content_type or "application/octet-stream",
        })

    history = session_store.get_messages(sid)
    creds_dict = session_store.get_google_credentials(sid)
    user_infos = session_store.get_user_info(sid) or {}

    try:
        factory = AgentFactory(llm=llm)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = factory.invoke(
        input_text=message,
        session_messages=history,
        uploaded_files=files_to_send,
        user_credentials=_build_credentials(creds_dict),
        user_infos=user_infos,
        session_id=sid,
    )

    outputs = result.get("output", [])
    reply_text = outputs[0]["content"] if outputs else ""

    # Persiste a mensagem do usuário e a(s) resposta(s) da Cidinha no histórico da sessão
    session_store.append_messages(sid, [{"role": "user", "content": message}] + outputs)
    updated_history = session_store.get_messages(sid)

    return ChatResponse(
        session_id=sid,
        reply=reply_text,
        history=[ChatMessage(**m) for m in updated_history],
    )


@router.get("/chat/{session_id}/history", response_model=HistoryResponse)
async def get_history(session_id: str, _api_key: None = Depends(verify_api_key)):
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail="Sessão não encontrada (ou expirada).")
    history = session_store.get_messages(session_id)
    return HistoryResponse(session_id=session_id, history=[ChatMessage(**m) for m in history])