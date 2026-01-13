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
        
        # Tenta buscar contexto, mas não falha se não achar
        try:
            collection = get_collection("shark_helper")
            # Se a pergunta for muito genérica, a busca pode não retornar nada relevante, e tudo bem.
            if temas:
                data = collection.query(query_texts=temas, n_results=3)
                documents = data["documents"]
            else:
                documents = []
        except Exception as e:
            print(f"Aviso RAG: {e}")
            documents = []
            
        end=time.time()
        print(f"Tempo gasto para RAG: {(end-start)}s")

        parser = StrOutputParser()
        llm = ChatGoogleGenerativeAI(
            model=Settings.gemini['model'],
            api_key=Settings.gemini['api_key'],
            temperature=0.5 # Aumentamos um pouco a temperatura para ser mais criativo fora do escopo
        )

        # ALTERAÇÃO 2: Prompt Híbrido (Contexto + Conhecimento Geral)
        prompt = PromptTemplate(
            template="""
            ### PAPEL
            Você é o **Mentor Especialista da SharkDev**.
            
            ### FONTE DE DADOS
            Abaixo estão trechos da nossa base de conhecimento interna.
            
            --- INÍCIO DO CONTEXTO SHARKDEV ---
            {data}
            --- FIM DO CONTEXTO SHARKDEV ---

            ### DIRETRIZES DE RESPOSTA
            1. **Prioridade:** Se a resposta estiver no [CONTEXTO SHARKDEV] acima, use-o como fonte principal e seja fiel a ele.
            2. **Flexibilidade (Escopo Geral):** Se a pergunta do usuário **NÃO** estiver relacionada ao contexto (ex: dúvidas de Python, perguntas gerais, ajuda criativa), **NÃO** diga que não sabe. Use seu vasto conhecimento de IA para responder de forma útil e didática.
            3. **Tom:** Profissional, encorajador e didático.
            
            ### ESTRUTURA DE RESPOSTA
            - Se usou o contexto SharkDev: Adicione um emoji 🦈 no início.
            - Se usou conhecimento geral: Responda naturalmente como um mentor experiente.
            - Sempre formate com Markdown (negrito, listas) para facilitar a leitura.

            ---
            ### PERGUNTA DO USUÁRIO
            {query}
            """,
            input_variables=["query", "data"]
        )

        chain = prompt | llm | parser

        start = time.time()
        # Passamos documents (pode estar vazio ou cheio)
        resposta = chain.invoke({"query": pergunta, "data": documents})
        end = time.time()

        print(f"Tempo gasto pela LLM: {(end-start)}s")
        return resposta