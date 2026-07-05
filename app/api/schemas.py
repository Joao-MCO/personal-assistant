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