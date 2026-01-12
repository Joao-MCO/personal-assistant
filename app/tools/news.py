import ast
import time
import uuid
from typing import Type, Union, Dict, Any
from langchain_core.tools import BaseTool
from langchain_community.chat_models import ChatMaritalk
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel
from models.tools import ReadNewsInput
from utils.settings import Settings
import requests
from datetime import date, timedelta

class ReadNews(BaseTool):
    name: str = "LerNoticias"
    description: str = """
    Utilize esta ferramenta sempre que for solicitado que você leia ou atualize alguém sobre as notícias diárias.
    """
    args_schema: Type[BaseModel] = ReadNewsInput
    return_direct: bool = True

    def _run(self, qtde_noticias: int = 10, assuntos: str = "", pais: str = "br") -> str:
        today = date.today()
        start_date = today - timedelta(days=30)
        query_param = f"q={assuntos}&" if assuntos else ""
        print(f"Filtros: \nQTD: {qtde_noticias}\nAssuntos: {assuntos}\nPaís: {pais}")
        url = (
            f"https://gnews.io/api/v4/search?{query_param}"
            f"lang=pt&max={qtde_noticias}&country={pais}"
            f"&from={start_date}&to={today}"
            f"&sortBy=publishedAt&apikey={Settings.gnews_api_key}"
        )

        start = time.time()
        response = requests.get(url)
        data = response.json()
        end = time.time()
        print(f"Tempo gasto pela API: {(end-start)}s")
        
        if 'articles' not in data:
            return "Não foi possível encontrar notícias ou houve erro na API."

        news_cleaned = []
        for article in data['articles']:
            news_cleaned.append({
                "title": article.get('title'),
                "description": article.get('description'),
                "content": article.get('content'),
                "source": article.get('source', {}).get('name')
            })

        if not news_cleaned:
            return f"Não encontrei notícias recentes sobre '{assuntos}' no país '{pais}'."

        parser = StrOutputParser()
        llm = ChatMaritalk(
            model=Settings.maritaca["model"],
            api_key=Settings.maritaca["api_key"],
            temperature=Settings.temperature,
            max_tokens=Settings.max_tokens
        )

        prompt = PromptTemplate(
            template="""
            ### PAPEL
            Você é um Editor Sênior. Sua tarefa é ler as notícias abaixo e criar **mini-artigos consolidados**.

            ### INSTRUÇÕES
            1. **Agrupamento:** Junte notícias sobre o mesmo tema.
            2. **Redação:** Escreva um texto fluido (não tópicos) para cada grupo.
            3. **Tamanho:** Escreva **2 parágrafos** para cada grupo. Seja detalhista, mas objetivo.
               - O texto deve ter entre 500 e 1000 caracteres por grupo (aprox. 150 palavras).

            ### FORMATO DE SAÍDA (Markdown)
            
            ## [Título Jornalístico do Grupo]
            **Fontes:** [Lista de Fontes]

            **Data:"" [Data da Notícia]

            [Parágrafo 1: O que aconteceu, quem, quando e onde...]

            [Parágrafo 2: Contexto, reações, citações ou desdobramentos...]

            ---
            ### NOTÍCIAS PARA ANÁLISE
            {news}
            """,
            input_variables=["news"]
        )

        chain = prompt | llm | parser

        start = time.time()
        response = chain.invoke({"news": str(news_cleaned)})
        end = time.time()

        print(f"Tempo gasto pela LLM: {(end-start)}s")

        return response