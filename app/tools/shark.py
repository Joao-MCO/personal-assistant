import time
import logging
from typing import List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from models.tools import SharkHelperInput
from services.chroma import get_collection
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

class SharkHelper(BaseTool):
    name: str = "AjudaShark"
    description: str = """
    Use esta ferramenta como PADRÃO para responder perguntas técnicas, dúvidas sobre a SharkDev (Blip, Bots, Processos),
    ou qualquer outra dúvida geral que NÃO seja sobre Agenda, Reuniões ou Notícias.
    """
    args_schema: Type[BaseModel] = SharkHelperInput
    return_direct: bool = True

    def _run(self, pergunta: str, temas: List[str]) -> str:
        # Log de entrada
        logger.info(f"Tool SharkHelper iniciada. Params: pergunta='{pergunta}', temas={temas}")
        
        start = time.time()
        try:
            # Garante que temas não seja None
            if not temas: temas = []
            
            # Adiciona a própria pergunta como tema para aumentar chances de match
            query_texts = temas + [pergunta]
            
            collection = get_collection("shark_helper")
            data = collection.query(query_texts=query_texts, n_results=5)
            documents = data.get("documents", [])
            
            # Flatten lista de listas (o Chroma retorna [[doc1, doc2]])
            flat_docs = [item for sublist in documents for item in sublist]
            
            if not flat_docs:
                logger.info("RAG Shark: Nenhum documento encontrado.")
                return "Não encontrei informações internas sobre esse assunto na base da SharkDev."
            
            logger.info(f"RAG Shark: {len(flat_docs)} documentos recuperados.")
            return "\n\n---\n\n".join(flat_docs)
            
        except Exception as e:
            logger.error(f"Erro RAG Shark: {e}")
            return "Erro ao consultar base de conhecimento."
            
        finally:
            end = time.time()
            logger.info(f"RAG Shark Tempo de execução: {end-start:.2f}s")