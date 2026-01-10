from typing import List
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
    temas: List[str] = Field(description="Lista dos principais temas. Limite Máximo: 5")