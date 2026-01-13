from typing import List, Optional
from pydantic import BaseModel, Field


class RPGQuestionInput(BaseModel):
    pergunta: str = Field(description="Pergunta informada pelo usuário.")
    temas: List[str] = Field(description="Lista dos principais temas. Limite Máximo: 5")

class GenericQuestionInput(BaseModel):
    pergunta: str = Field(description="Pergunta informada pelo usuário.")

class ReadNewsInput(BaseModel):
    qtde_noticias: int = Field(default=5, description="Quantidade de notícias a serem buscadas.")
    assuntos: str = Field(default="", description="Temas ou palavras-chave da pesquisa.")
    pais: str = Field(default="br", description="Sigla do País ao qual se refere as notícias desejadas. (Ex: ar, br, us, en)")

class CodeHelperInput(BaseModel):
    pergunta: str = Field(description="Pergunta ou código informado pelo usuário para análise.")

class SharkHelperInput(BaseModel):
    pergunta: str = Field(description="Pergunta informada pelo usuário.")
    temas: List[str] = Field(defaul=[], description="Lista dos principais temas. Limite Máximo: 5")

class DateParts(BaseModel):
    day: int = Field(description="Dia do mês (1-31)")
    month: int = Field(description="Mês (1-12)")
    year: int = Field(description="Ano (ex: 2026)")
    hours: int = Field(description="Hora (0-23)")
    minutes: int = Field(description="Minutos (0-59)")
class CreateEventInput(BaseModel):
    meeting_date: DateParts = Field(description="Data, Horas e Minutos da reunião")
    description: str = Field(description="Título do evento")
    attendees: Optional[List[str]] = Field(default=None, description="Lista de e-mails")
    meet_length: int = Field(default=30, description="Duração em minutos")
    timezone: str = Field(default="America/Sao_Paulo")

class CheckCalendarInput(BaseModel):
    start_date: DateParts = Field(description="Data, Horas e Minutos iniciais do filtro de pesquisa")
    end_date: DateParts = Field(description="Data, Horas e Minutos finais do filtro de pesquisa")
    email: str = Field(description="Email a ser verificado.")
class CheckEmailInput(BaseModel):
    max_results: int = Field(default=5, description="Quantidade de emails a serem conferidos")
    query: Optional[str] = Field(default=None, description="Palavra-chave ou frase para buscar no assunto ou corpo do email.")
    data_inicio: Optional[str] = Field(default=None, description="Data inicial para o filtro (formato YYYY/MM/DD).")
    data_fim: Optional[str] = Field(default=None, description="Data final para o filtro (formato YYYY/MM/DD).")