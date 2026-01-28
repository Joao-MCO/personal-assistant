import logging
from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from duckduckgo_search import DDGS
from models.tools import WebSearchInput

logger = logging.getLogger(__name__)

class WebSearch(BaseTool):
    name: str = "PesquisaWeb"
    description: str = """
    Utilize para buscar informações na internet que NÃO sejam notícias de última hora.
    Ideal para: documentações técnicas, erros de código, datas históricas, sites oficiais e fact-checking.
    """
    args_schema: Type[BaseModel] = WebSearchInput
    return_direct: bool = False

    def _run(self, query: str, max_results: int = 5) -> str:
        logger.info(f"🔍 Tool WebSearch iniciada. Query: '{query}'")
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(keywords=query, max_results=max_results))

            if not results:
                return "Nenhum resultado relevante encontrado na web."

            output = [f"Resultados para: '{query}'\n"]
            
            for i, res in enumerate(results, 1):
                title = res.get('title', 'Sem título')
                link = res.get('href', '#')
                body = res.get('body', 'Sem descrição')
                
                output.append(f"Result #{i}")
                output.append(f"Título: {title}")
                output.append(f"Link: {link}")
                output.append(f"Resumo: {body}\n---")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Erro na WebSearch: {e}", exc_info=True)
            return f"Erro ao realizar pesquisa na web: {str(e)}"