import time
from typing import List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from models.tools import SharkHelperInput
from services.chroma import get_collection
from utils.settings import WrappedSettings as Settings

class SharkHelper(BaseTool):
    name: str = "AjudaShark"
    description: str = """
    Use esta ferramenta como PADRÃO para responder perguntas técnicas, dúvidas sobre a SharkDev (Blip, Bots, Processos),
    ou qualquer outra dúvida geral que NÃO seja sobre Agenda, Reuniões ou Notícias.
    """
    args_schema: Type[BaseModel] = SharkHelperInput
    return_direct: bool = True

    def _run(self, pergunta: str, temas: List[str]) -> str:
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
                return "Não encontrei informações internas sobre esse assunto na base da SharkDev."
                
            return "\n\n---\n\n".join(flat_docs)
            
        except Exception as e:
            print(f"Erro RAG Shark: {e}")
            return "Erro ao consultar base de conhecimento."
            
        finally:
            end = time.time()
            print(f"⏱️ RAG Shark: {end-start:.2f}s")