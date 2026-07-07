import logging
import time
from typing import ClassVar, Dict, Type

from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from agent.llm_factory import LLMFactory
from models.tools import TradutorTecnicoInput
from services.llm_usage import log_llm_call

logger = logging.getLogger(__name__)


class TradutorTecnico(BaseTool):
    name: str = "TradutorTecnico"
    description: str = """
    Use para traduzir texto técnico (documentação, comentários de código,
    mensagens de commit, etc.) entre português e inglês.
    """
    args_schema: Type[BaseModel] = TradutorTecnicoInput
    return_direct: bool = True

    MODEL_FAMILY: ClassVar[str] = "gemini"
    IDIOMAS: ClassVar[Dict[str, str]] = {"en": "inglês", "pt": "português"}
    TEMPLATE: ClassVar[str] = """Traduza o texto técnico abaixo para {idioma_destino}. Preserve formatação (markdown, blocos de código, nomes de variáveis/funções não devem ser traduzidos) e termos técnicos que normalmente não se traduzem (ex: nomes de bibliotecas, "commit", "pull request").

Devolva SOMENTE a tradução, sem explicações antes ou depois.

Texto:
{texto}
"""

    def _run(self, texto: str, destino: str) -> str:
        start = time.time()
        try:
            llm = LLMFactory.create_llm_fast(self.MODEL_FAMILY)
            prompt = PromptTemplate.from_template(self.TEMPLATE).format(
                texto=texto, idioma_destino=self.IDIOMAS.get(destino, destino)
            )
            response = llm.invoke(prompt)
            log_llm_call(model_family=self.MODEL_FAMILY, skill_name=self.name, llm_response=response)
            return response.content
        except (ValueError, RuntimeError) as e:
            logger.error(f"{self.name}: erro ao usar LLM ({self.MODEL_FAMILY}): {e}")
            return f"Não consegui traduzir agora: {e}"
        finally:
            logger.info(f"{self.name} — tempo de execução: {time.time() - start:.2f}s")