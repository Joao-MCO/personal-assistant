"""
Armazenamento de sessões de conversa -- agora em SQL (tabelas `sessions`,
`messages`, `google_credentials`), não mais em memória.

A interface pública é EXATAMENTE a mesma da versão anterior (mesmos métodos,
mesmas assinaturas, mesmo `session_store` como instância única importável) --
só o que muda é o que acontece por dentro de cada método. Isso significa que
`app/api/chat.py` e `app/api/auth.py` não precisaram mudar nenhuma chamada a
`session_store.*` por causa desta migração.

O que se ganha: o histórico e as credenciais Google sobrevivem a um
restart/deploy do processo (antes, um dict em memória, zerava toda vez) e,
se DATABASE_URL apontar para Postgres, ficam visíveis para múltiplas
instâncias/workers ao mesmo tempo -- o que a versão em memória não permitia.

Uma simplificação deliberada em relação à versão anterior: não há mais uma
rotina ativa de "purge" de sessões expiradas. Na versão em memória isso era
necessário para não vazar RAM indefinidamente; numa tabela em disco, uma
sessão expirada que ninguém mais acessa não causa o mesmo tipo de problema --
ela só deixa de ser considerada válida por `exists()`/`get_or_create()`
(comparando `last_active` contra o TTL), mas a linha continua no banco
disponível para consulta/auditoria caso um dia isso seja útil.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from db.base import SessionLocal
from db.models import GoogleCredential, Message, SessionModel
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite não guarda timezone -- ao reler, trata datetime "naive" como UTC (é como foi gravado)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class SessionStore:
    def __init__(self, ttl_minutes: Optional[int] = None):
        self._ttl = timedelta(minutes=ttl_minutes or Settings.session_ttl_minutes or 120)

    # ------------------------------------------------------------------
    # Ciclo de vida da sessão
    # ------------------------------------------------------------------

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            db.add(SessionModel(id=session_id))
            db.commit()
        finally:
            db.close()
        logger.info(f"Sessão criada: {session_id}")
        return session_id

    def exists(self, session_id: str) -> bool:
        db = SessionLocal()
        try:
            row = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if row is None:
                return False
            return (_utcnow() - _as_aware(row.last_active)) <= self._ttl
        finally:
            db.close()

    def get_or_create(self, session_id: Optional[str]) -> str:
        """Reaproveita a sessão se ela existir e ainda for válida; senão cria uma nova."""
        if session_id:
            db = SessionLocal()
            try:
                row = db.query(SessionModel).filter(SessionModel.id == session_id).first()
                if row is not None and (_utcnow() - _as_aware(row.last_active)) <= self._ttl:
                    row.last_active = _utcnow()
                    db.commit()
                    return session_id
            finally:
                db.close()
        return self.create()

    # ------------------------------------------------------------------
    # Histórico de conversa
    # ------------------------------------------------------------------

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            rows = (
                db.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.id.asc())
                .all()
            )
            return [{"role": r.role, "content": r.content} for r in rows]
        finally:
            db.close()

    def append_messages(self, session_id: str, new_messages: List[Dict[str, Any]]) -> None:
        db = SessionLocal()
        try:
            if db.query(SessionModel).filter(SessionModel.id == session_id).first() is None:
                db.add(SessionModel(id=session_id))
                db.flush()
            for m in new_messages:
                db.add(Message(
                    session_id=session_id,
                    role=str(m.get("role", "user")),
                    content=str(m.get("content", "")),
                ))
            db.query(SessionModel).filter(SessionModel.id == session_id).update({"last_active": _utcnow()})
            db.commit()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Credenciais Google (OAuth)
    # ------------------------------------------------------------------

    def set_google_credentials(self, session_id: str, credentials: Optional[Dict[str, Any]]) -> None:
        db = SessionLocal()
        try:
            existing = db.query(GoogleCredential).filter(GoogleCredential.session_id == session_id).first()

            if credentials is None:
                if existing is not None:
                    db.delete(existing)
                    db.commit()
                return

            if db.query(SessionModel).filter(SessionModel.id == session_id).first() is None:
                db.add(SessionModel(id=session_id))
                db.flush()

            if existing is None:
                existing = GoogleCredential(session_id=session_id)
                db.add(existing)

            existing.token = credentials.get("token")
            existing.refresh_token = credentials.get("refresh_token")
            existing.token_uri = credentials.get("token_uri")
            existing.client_id = credentials.get("client_id")
            existing.client_secret = credentials.get("client_secret")
            existing.scopes = json.dumps(credentials.get("scopes") or [])
            db.commit()
        finally:
            db.close()

    def get_google_credentials(self, session_id: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            row = db.query(GoogleCredential).filter(GoogleCredential.session_id == session_id).first()
            if row is None:
                return None
            return {
                "token": row.token,
                "refresh_token": row.refresh_token,
                "token_uri": row.token_uri,
                "client_id": row.client_id,
                "client_secret": row.client_secret,
                "scopes": json.loads(row.scopes) if row.scopes else [],
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Dados do usuário (nome/email amigáveis, preenchidos após o login Google)
    # ------------------------------------------------------------------

    def set_user_info(self, session_id: str, user_info: Optional[Dict[str, Any]]) -> None:
        db = SessionLocal()
        try:
            row = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if row is None:
                row = SessionModel(id=session_id)
                db.add(row)
            row.user_name = user_info.get("user") if user_info else None
            row.user_email = user_info.get("email") if user_info else None
            db.commit()
        finally:
            db.close()

    def get_user_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            row = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if row is None or not (row.user_name or row.user_email):
                return None
            return {"user": row.user_name, "email": row.user_email}
        finally:
            db.close()


# Instância única compartilhada pela aplicação inteira.
session_store = SessionStore()