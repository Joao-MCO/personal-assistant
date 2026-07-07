"""
RAGDaBaseDeCodigo e OnboardingGuiado -- mesmo padrão de RAG que o AjudaShark
já usa (tools/shark.py), cada uma numa coleção diferente do Chroma. A lógica
de consulta é idêntica entre as duas, então vive numa classe base comum
(_RAGToolBase) -- cada subclasse só declara nome, descrição, schema e qual
coleção consultar.

Para popular as coleções, use services/text_ingestion.py:
    from services.text_ingestion import create_text_embedding
    create_text_embedding("codebase_docs", "dados_codigo")
    create_text_embedding("onboarding_docs", "dados_onboarding")
"""

import logging
import time
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from models.tools import OnboardingInput, RAGCodebaseInput
from services.chroma import get_collection

logger = logging.getLogger(__name__)


class _RAGToolBase(BaseTool):
    """Base compartilhada -- subclasses só definem name/description/args_schema/collection_name."""

    collection_name: str = ""
    n_results: int = 5

    def _run(self, pergunta: str) -> str:
        start = time.time()
        try:
            collection = get_collection(self.collection_name)
            data = collection.query(query_texts=[pergunta], n_results=self.n_results)
            documents = data.get("documents", [])
            flat_docs = [item for sublist in documents for item in sublist]

            if not flat_docs:
                return f"Não encontrei informações sobre isso na base '{self.collection_name}'."

            return "\n\n---\n\n".join(flat_docs)
        except Exception as e:
            logger.error(f"{self.name}: erro ao consultar Chroma ({self.collection_name}): {e}")
            return f"Erro ao consultar a base de conhecimento: {e}"
        finally:
            logger.info(f"{self.name} — tempo de execução: {time.time() - start:.2f}s")


class RAGDaBaseDeCodigo(_RAGToolBase):
    name: str = "RAGDaBaseDeCodigo"
    description: str = """
    Use para dúvidas técnicas sobre a base de código dos repositórios da
    SharkDev: arquitetura, decisões de design (ADRs), como um serviço
    específico funciona, convenções internas de código. Diferente do
    AjudaShark, que é sobre processos/Blip — esta é especificamente sobre
    código e arquitetura de software.
    """
    args_schema: Type[BaseModel] = RAGCodebaseInput
    collection_name: str = "codebase_docs"
    return_direct: bool = False


class OnboardingGuiado(_RAGToolBase):
    name: str = "OnboardingGuiado"
    description: str = """
    Use para dúvidas de quem está em onboarding na SharkDev: por onde
    começar, como configurar o ambiente, quem é responsável por qual
    sistema, processos iniciais.
    """
    args_schema: Type[BaseModel] = OnboardingInput
    collection_name: str = "onboarding_docs"
    return_direct: bool = False