from typing import List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from models.tools import SharkHelperInput
from services.chroma import get_collection
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores.chroma import Chroma
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.settings import Settings

class SharkHelper(BaseTool):
    name: str = "AjudaShark"
    # ALTERAÇÃO 1: Descrição mais ampla para a LLM escolher essa tool com mais frequência
    description: str = """
    Use esta ferramenta como PADRÃO para responder perguntas técnicas, dúvidas sobre a SharkDev (Blip, Bots),
    ou qualquer outra dúvida geral que NÃO seja sobre Agenda, Reuniões ou Notícias.
    """
    args_schema: Type[BaseModel] = SharkHelperInput
    return_direct: bool = True

    def _run(self, pergunta: str, temas: List[str]) -> str:
        start = time.time()
        try:
            collection = get_collection("shark_helper")
            if temas:
                data = collection.query(query_texts=temas, n_results=5)
                documents = data["documents"]
            else:
                documents = []
        except Exception as e:
            print(f"Aviso RAG: {e}")
            documents = []
            
        end=time.time()
        print(f"Tempo gasto para RAG: {(end-start)}s")
        return documents