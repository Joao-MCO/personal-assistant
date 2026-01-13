import ast
import time
import uuid
from typing import List, Type, Union, Dict, Any
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel
from models.tools import GenericQuestionInput, RPGQuestionInput
from services.chroma import get_collection
from utils.settings import Settings
    
class RPGQuestion(BaseTool):
    name: str = "DuvidasRPG"
    description: str = """
    Utilize esta ferramenta sempre que for feita uma pergunta sobre o jogo de Interpretação de Papéis (RPG) Dungeons & Dragons.
    """
    args_schema: Type[BaseModel] = RPGQuestionInput
    return_direct: bool = True

    def _run(self, pergunta: str, temas: List[str] = "") -> str:
        start = time.time()
        query = pergunta
        collection = get_collection("my_collection")
        data = collection.query(query_texts=temas, n_results=100)
        end = time.time()

        print(f"Tempo gasto para RAG: {(end-start)}s")
        parser = StrOutputParser()
        llm = ChatGoogleGenerativeAI(
            model=Settings.gemini["model"],
            api_key=Settings.gemini["api_key"]
        )

        prompt = PromptTemplate(
            template="""
            ### PAPEL
            Você é o **Sábio de Candlekeep**, um especialista absoluto em Dungeons & Dragons 5ª Edição (D&D 5e). Baseie-se no conjunto de textos para ajudar sua resposta ser mais precisa.

            ### OBJETIVOS
            1.  **Clarificar Regras:** Explicar mecânicas de jogo com precisão, citando a lógica oficial (RAW - Rules as Written) e a intenção da regra (RAI - Rules as Intended) quando necessário.
            2.  **Auxiliar na Criação:** Ajudar a montar fichas, explicar classes, calcular atributos e sugerir antecedentes (backgrounds).
            3.  **Inspirar Narrativa:** Ajudar Mestres com ganchos de aventura, balanceamento de encontros e descrições de itens mágicos.

            ### DIRETRIZES DE RESPOSTA
            * **Citação de Fontes:** Sempre que explicar uma regra, mencione a fonte oficial (ex: "Conforme o PHB, pág. 192...").
            * **Mecânica vs. Narrativa:** Separe claramente o que é número/regra (mecânica) do que é descrição/história (flavor).
            * **Didática:** Se a regra for complexa (ex: Agarrar/Grapple ou Ataque Furtivo), use um exemplo prático de combate.
            * **Regra da Casa (Homebrew):** Se a pergunta envolver algo que não existe nas regras oficiais, avise que é "Homebrew" e sugira uma forma equilibrada de resolver.
            * **Idioma:** Responda em Português, mas mantenha os termos técnicos principais em inglês entre parênteses para facilitar a consulta (ex: "Teste de Resistência (Saving Throw)").
            * **Fonte de Dados:** Sempre confirme se sua resposta está condizente com os dados vindos do [CONJUNTO DE TEXTOS BASE].

            ### ESTRUTURA DE RESPOSTA (Markdown)

            ## 🎲 Resposta da Regra
            [Explicação direta e concisa da regra oficial]

            ### 📜 Exemplo Prático
            [Um cenário curto: "O Ladino tenta se esconder atrás de uma caixa..."]

            ### 💡 Dica do Sábio
            [Uma sugestão estratégica, combo ou variação para Mestres]

            ---
            ### ENTRADA DO USUÁRIO
            {query}

            ### CONJUNTO DE TEXTOS BASE
            {data}
            """,
            input_variables=["query", {"text": data['documents'], "metadata": data["metadatas"]}]
        )

        chain = prompt | llm | parser

        start = time.time()
        resposta = chain.invoke({"query": query, "data": data})
        end = time.time()

        print(f"Tempo gasto pela LLM: {(end-start)}s")

        return resposta