"""
Armazenamento de sessões de conversa para a API.

Cada sessão guarda o que antes vivia no `st.session_state` do Streamlit:
- o histórico de mensagens da conversa
- as credenciais OAuth do Google (se o usuário já fez login)
- os dados do usuário (nome amigável + email), usados para personalizar o
  contexto passado ao agente

Implementação atual: em memória, em um único processo (um dict com lock,
no mesmo espírito do ToolResultCache que já existia no projeto). Isso é
suficiente para começar, mas tem duas limitações a ter em mente:
1. Reinicia zerado a cada deploy/restart do processo.
2. Não funciona se a API rodar em múltiplas instâncias/processos (cada uma
   teria seu próprio dicionário, sem saber da sessão criada na outra).

Quando isso passar a ser um problema (mais usuários, precisa de múltiplas
instâncias, ou precisa sobreviver a restarts), o caminho natural é reescrever
esta classe para usar Redis — as variáveis REDIS_HOST/PORT/DB/PASSWORD já
existem em utils/settings.py para isso — mantendo os mesmos métodos públicos,
de forma que o restante da API (app/api/chat.py, app/api/auth.py) não precise
mudar nada.
"""

import time
import uuid
import logging
from threading import Lock
from typing import Any, Dict, List, Optional

from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)


class SessionStore:
    def __init__(self, ttl_minutes: Optional[int] = None):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        ttl_minutes = ttl_minutes or Settings.session_ttl_minutes or 120
        self._ttl_seconds = ttl_minutes * 60

    # ------------------------------------------------------------------
    # Ciclo de vida da sessão
    # ------------------------------------------------------------------

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = self._blank_session()
        logger.info(f"Sessão criada: {session_id}")
        return session_id

    def exists(self, session_id: str) -> bool:
        with self._lock:
            self._purge_expired()
            return session_id in self._sessions

    def get_or_create(self, session_id: Optional[str]) -> str:
        """Reaproveita a sessão se ela existir e ainda for válida; senão cria uma nova."""
        if session_id:
            with self._lock:
                self._purge_expired()
                if session_id in self._sessions:
                    self._sessions[session_id]["last_active"] = time.time()
                    return session_id
        return self.create()

    # ------------------------------------------------------------------
    # Histórico de conversa
    # ------------------------------------------------------------------

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            return list(session["messages"]) if session else []

    def append_messages(self, session_id: str, new_messages: List[Dict[str, Any]]) -> None:
        with self._lock:
            session = self._sessions.setdefault(session_id, self._blank_session())
            session["messages"].extend(new_messages)
            session["last_active"] = time.time()

    # ------------------------------------------------------------------
    # Credenciais Google (OAuth)
    # ------------------------------------------------------------------

    def set_google_credentials(self, session_id: str, credentials: Optional[Dict[str, Any]]) -> None:
        with self._lock:
            session = self._sessions.setdefault(session_id, self._blank_session())
            session["google_credentials"] = credentials
            session["last_active"] = time.time()

    def get_google_credentials(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            return session["google_credentials"] if session else None

    # ------------------------------------------------------------------
    # Dados do usuário (preenchidos após o login Google)
    # ------------------------------------------------------------------

    def set_user_info(self, session_id: str, user_info: Optional[Dict[str, Any]]) -> None:
        with self._lock:
            session = self._sessions.setdefault(session_id, self._blank_session())
            session["user_info"] = user_info

    def get_user_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            return session["user_info"] if session else None

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _blank_session(self) -> Dict[str, Any]:
        now = time.time()
        return {
            "messages": [],
            "google_credentials": None,
            "user_info": None,
            "created_at": now,
            "last_active": now,
        }

    def _purge_expired(self) -> None:
        """Remove sessões inativas há mais tempo que o TTL. Deve ser chamado sob self._lock."""
        now = time.time()
        expired = [
            sid for sid, data in self._sessions.items()
            if now - data["last_active"] > self._ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info(f"{len(expired)} sessão(ões) expirada(s) removida(s) por inatividade.")


# Instância única compartilhada pela aplicação inteira.
session_store = SessionStore()