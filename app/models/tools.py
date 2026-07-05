from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# =========================================
# 1. Ferramentas de Informação (Shark)
# =========================================

class SharkHelperInput(BaseModel):
    pergunta: str = Field(
        ..., 
        description="A dúvida do usuário relacionada à SharkDev, processos internos ou plataforma Blip."
    )
    temas: List[str] = Field(
        default=[], 
        description="Lista de palavras-chave (tags) para auxiliar a busca no banco vetorial."
    )

# =========================================
# 2. Ferramentas de Produtividade (Google)
# =========================================

class CheckCalendarInput(BaseModel):
    start_date: dict = Field(
        ..., 
        description="Objeto representando a data de início da busca (chaves: year, month, day, hours, minutes)."
    )
    end_date: dict = Field(
        ..., 
        description="Objeto representando a data de fim da busca (chaves: year, month, day, hours, minutes)."
    )
    email: str = Field(
        default="primary", 
        description="ID do calendário a ser verificado (geralmente o email). Use 'primary' para o padrão."
    )

class CheckEmailInput(BaseModel):
    max_results: int = Field(
        default=5, 
        description="Número máximo de e-mails recentes a serem recuperados."
    )
    query: Optional[str] = Field(
        default=None, 
        description="Termo de busca para filtrar e-mails (ex: 'assunto:Reunião', 'from:chefe@empresa.com'). Se vazio, traz os mais recentes."
    )
    data_inicio: Optional[str] = Field(
        default=None, 
        description="Data inicial opcional para filtro (formato YYYY/MM/DD)."
    )
    data_fim: Optional[str] = Field(
        default=None, 
        description="Data final opcional para filtro (formato YYYY/MM/DD)."
    )

class SendEmailInput(BaseModel):
    to: str = Field(
        ..., 
        description="Endereço de e-mail do destinatário."
    )
    subject: str = Field(
        ..., 
        description="Assunto do e-mail."
    )
    body: str = Field(
        ..., 
        description="Conteúdo da mensagem."
    )
    body_type: Literal['plain', 'html'] = Field(
        default='plain', 
        description="Formato do corpo do e-mail: use 'plain' para texto simples ou 'html' para formatação rica."
    )

class CreateEventInput(BaseModel):
    meeting_date: dict = Field(
        ..., 
        description="Objeto com a data/hora de início da reunião (year, month, day, hours, minutes)."
    )
    description: str = Field(
        ..., 
        description="Título e descrição do evento (ex: 'Daily | Ana <> Pedro')."
    )
    attendees: Optional[List[str]] = Field(
        default=None, 
        description="Lista de e-mails dos convidados."
    )
    meet_length: int = Field(
        default=30, 
        description="Duração da reunião em minutos."
    )
    timezone: str = Field(
        default="America/Sao_Paulo", 
        description="Fuso horário do evento."
    )