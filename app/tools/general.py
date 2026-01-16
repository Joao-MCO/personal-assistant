import time
from typing import List, Type
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel
from models.tools import RPGQuestionInput
from services.chroma import get_collection
from utils.settings import WrappedSettings as Settings
from prompts.templates import RPG_HELPER_PROMPT

class RPGQuestion(BaseTool):
    name: str = "DuvidasRPG"
    description: str = "Tira dúvidas de regras e lore de D&D 5e."
    args_schema: Type[BaseModel] = RPGQuestionInput
    return_direct: bool = True
    
    _chain: object = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        llm = ChatGoogleGenerativeAI(
            model=Settings.gemini["model"],
            api_key=Settings.gemini["api_key"],
            temperature=0.3
        )
        prompt = PromptTemplate(
            template=RPG_HELPER_PROMPT,
            input_variables=["query", "data"]
        )
        self._chain = prompt | llm | StrOutputParser()

    def _run(self, pergunta: str, temas: List[str] = []) -> str:
        start = time.time()
        try:
            collection = get_collection("my_collection")
            query_temas = temas if temas else [pergunta]
            data = collection.query(query_texts=query_temas, n_results=3) 
            
            docs_text = "\n".join(data['documents'][0]) if data['documents'] else "Sem contexto adicional."
            
            # Geração
            resposta = self._chain.invoke({"query": pergunta, "data": docs_text})
            print(f"⏱️ RPG Helper: {time.time()-start:.2f}s")
            return resposta
        except Exception as e:
            return f"Erro ao consultar o oráculo: {e}"