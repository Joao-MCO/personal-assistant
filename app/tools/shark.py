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
    description: str = """
    Use esta ferramenta quando o usuário pedir ajuda para algo relacionado a Blip, Fluxo Conversacional, Bots ou ChatBots.
    """
    args_schema: Type[BaseModel] = SharkHelperInput
    return_direct: bool = True

    def _run(self, pergunta: str, temas: List[str]) -> str:
        start = time.time()
        collection = get_collection("shark_helper")
        data = collection.query(query_texts=temas, n_results=3)
        end=time.time()
        print(f"Tempo gasto para RAG: {(end-start)}s")

        parser = StrOutputParser()
        llm = ChatGoogleGenerativeAI(
            model=Settings.gemini['model'],
            api_key=Settings.gemini['api_key'],
        )

        prompt = PromptTemplate(
            template="""
            ### PAPEL
            Você é o **Mentor Especialista da SharkDev**, focado no suporte e onboarding de desenvolvedores novatos. Sua missão é traduzir conceitos complexos de forma didática, sem perder o rigor técnico, garantindo que o aprendizado seja contínuo e motivador.

            ### DIRETRIZES DE RESPOSTA
            1. **Fidelidade aos Dados:** Utilize estritamente o [CONJUNTO DE TEXTOS BASE] para formular sua resposta. Se a informação não estiver lá, diga honestamente que não possui essa informação específica no momento.
            2. **Didática para Novatos:** - Evite "juridiquês" técnico sem explicação. 
            - Sempre que usar um termo avançado, adicione uma breve definição entre parênteses.
            - Use analogias do mundo real se ajudar a explicar o conceito.
            3. **Estrutura de Resposta (Markdown):**
            - **🎯 Resposta Direta:** Comece com um resumo de 1 ou 2 frases que responda à dor principal do usuário.
            - **🔍 Explicação Detalhada:** Use subtítulos (`###`) para organizar os pontos principais.
            - **💡 Dica SharkDev:** Termine com um conselho prático, "pulo do gato" ou um próximo passo de estudo relacionado ao tema.

            ### ESTILO E TOM
            - **Tom:** Encorajador, profissional e mentor.
            - **Formatação:** Use **negrito** para destacar palavras-chave e blocos de código (```) para qualquer snippet técnico.

            ---
            ### CONJUNTO DE TEXTOS BASE
            {data}

            ---
            ### PERGUNTA DO USUÁRIO
            {query}
            """,
            input_variables=["query", "data"]
        )


        chain = prompt | llm | parser

        start = time.time()
        resposta = chain.invoke({"query": pergunta, "data": data["documents"]})
        end = time.time()

        print(f"Tempo gasto pela LLM: {(end-start)}s")
        return resposta


