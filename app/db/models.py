"""
Modelos SQLAlchemy. Cada tabela aqui corresponde a um dos usos discutidos
antes de partir pro código:

- SessionModel + Message  -> histórico de conversa (antes: SessionStore em memória)
- GoogleCredential        -> credenciais OAuth do Google por sessão (antes: dentro do SessionStore em memória)
- Employee                -> contatos internos da SharkDev (antes: app/assets/emails.json)
- ApiClient               -> clientes da API com chave individual revogável (antes: uma única API_KEY)
- ToolCall                -> auditoria + analytics de uso das ferramentas (unificação de "agent_actions" e "tool_usage")
- KnowledgeDocument       -> controle de quais arquivos já foram indexados no Chroma (Shark Helper)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class SessionModel(Base):
    """Uma conversa com a Cidinha. `id` é o `session_id` usado em toda a API."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_new_uuid)
    user_name = Column(String, nullable=True)
    user_email = Column(String, nullable=True)
    # Link formal com o funcionário, preenchido no callback do OAuth (auth.py)
    # quando o e-mail da conta Google logada bate com um Employee. Antes esse
    # "match" só acontecia em tempo de execução (comparação de string), sem
    # nenhuma relação persistida -- isso formaliza como chave estrangeira de
    # verdade, e é o que a checagem de permissões usa.
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    last_active = Column(DateTime, default=_utcnow)

    messages = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan"
    )
    google_credential = relationship(
        "GoogleCredential",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    session = relationship("SessionModel", back_populates="messages")


class GoogleCredential(Base):
    """Token OAuth do Google associado a uma sessão. 1:1 com SessionModel."""

    __tablename__ = "google_credentials"

    session_id = Column(String, ForeignKey("sessions.id"), primary_key=True)
    token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_uri = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    scopes = Column(Text, nullable=False)  # lista serializada em JSON
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    session = relationship("SessionModel", back_populates="google_credential")


class Employee(Base):
    """Contato interno da SharkDev. Antes: app/assets/emails.json (que agora só alimenta a seed inicial)."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    ativo = Column(Boolean, default=True)
    # "admin" | "member" | "guest" -- define o conjunto padrão de ferramentas
    # que a pessoa pode usar em conversa (ver services/permissions.py).
    # Não é um Enum de banco de propósito: adicionar um cargo novo não deve
    # exigir uma migração de schema, só atualizar o mapeamento em código.
    role = Column(String, nullable=False, default="member")
    created_at = Column(DateTime, default=_utcnow)


class EmployeeToolGrant(Base):
    """
    Exceção de permissão POR FUNCIONÁRIO, além do que o cargo (Employee.role)
    já concede por padrão. `granted=True` libera uma ferramenta que o cargo
    não liberaria; `granted=False` bloqueia uma que o cargo liberaria. Se não
    existir linha aqui para (employee, tool), vale o padrão do cargo -- ver
    services/permissions.py.
    """

    __tablename__ = "employee_tool_grants"
    __table_args__ = (UniqueConstraint("employee_id", "tool_name", name="uq_employee_tool"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    tool_name = Column(String, nullable=False)
    granted = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class ApiClient(Base):
    """Cliente autorizado a chamar /chat. Guarda só o hash da chave -- o texto puro nunca é persistido."""

    __tablename__ = "api_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True, index=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    last_used_at = Column(DateTime, nullable=True)


class ToolCall(Base):
    """
    Registro unificado de auditoria + analytics de cada chamada de ferramenta
    feita pelo agente (Calendar, Gmail, Shark Helper...).

    Consolida os dois exemplos discutidos antes de partir pro código
    ("agent_actions" para auditoria e "tool_usage" para analytics) numa
    tabela só -- as colunas se sobrepunham quase por completo, então manter
    duas só duplicaria escrita a cada chamada sem ganho real de consulta.
    Auditoria = SELECT olhando `params`/`result`; analytics = SELECT
    agregando `duration_ms`/`success`.
    """

    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=True, index=True)
    tool_name = Column(String, nullable=False, index=True)
    params = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)


class KnowledgeDocument(Base):
    """Controle de quais arquivos já foram indexados no Chroma pelo Shark Helper (app/utils/embedding.py)."""

    __tablename__ = "knowledge_documents"
    __table_args__ = (UniqueConstraint("collection", "filename", name="uq_knowledge_doc"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    num_pages = Column(Integer, nullable=True)
    content_hash = Column(String, nullable=True)
    indexed_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class LLMCall(Base):
    """
    Registro de cada chamada a um LLM (orquestrador OU o LLM interno de uma
    skill especialista), para o MonitorDeCustosLLM. Diferente de `ToolCall`:
    aquela tabela audita ferramentas (Calendar, Gmail...); esta audita
    especificamente invocações de modelo de linguagem, com tokens e custo
    estimado -- coisas que só fazem sentido para chamadas de LLM.
    """

    __tablename__ = "llm_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=True, index=True)
    model = Column(String, nullable=False, index=True)
    skill_name = Column(String, nullable=False, index=True)  # "orchestrator" ou o nome da skill especialista
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)