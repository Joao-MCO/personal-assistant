from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' ou 'assistant'")
    content: str


class ChatResponse(BaseModel):
    session_id: str = Field(
        ...,
        description="Guarde este id e reenvie nas próximas chamadas para continuar a mesma conversa."
    )
    reply: str = Field(..., description="Resposta da Cidinha para esta mensagem.")
    history: List[ChatMessage] = Field(..., description="Histórico completo da conversa até agora.")


class HistoryResponse(BaseModel):
    session_id: str
    history: List[ChatMessage]


class GoogleStatusResponse(BaseModel):
    session_id: str
    connected: bool
    email: Optional[str] = None
    name: Optional[str] = None


# ---------------------------------------------------------------------------
# Administração: funcionários (antes: app/assets/emails.json)
# ---------------------------------------------------------------------------

class EmployeeCreate(BaseModel):
    nome: str
    email: str


class EmployeeOut(BaseModel):
    id: int
    nome: str
    email: str
    ativo: bool


# ---------------------------------------------------------------------------
# Administração: clientes da API (antes: uma única API_KEY no .env)
# ---------------------------------------------------------------------------

class ApiClientCreate(BaseModel):
    name: str


class ApiClientCreated(BaseModel):
    id: int
    name: str
    api_key: str = Field(..., description="Só aparece aqui, nesta resposta. Guarde-a — não é recuperável depois.")


class ApiClientOut(BaseModel):
    id: int
    name: str
    active: bool