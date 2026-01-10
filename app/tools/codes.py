import time
from typing import  Type
from pydantic import BaseModel
from langchain_core.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from models.tools import CodeHelperInput
from utils.settings import Settings

class CodeHelper(BaseTool):
    name: str = "AjudaProgramacao"
    description: str = """
    Use esta ferramenta quando o usuário pedir ajuda para escrever código, 
    depurar erros (debugging), explicar conceitos de programação ou refatorar scripts.
    """
    args_schema: Type[BaseModel] = CodeHelperInput
    return_direct: bool = True

    def _run(self, pergunta: str) -> str:
        query = pergunta

        parser = StrOutputParser()

        llm = ChatAnthropic(
            model=Settings.claude["model"],
            api_key=Settings.claude["api_key"],
            temperature=0.2,
            max_tokens=8000
        )

        prompt = PromptTemplate(
            template="""
            ### PAPEL
            Você é um Engenheiro de Software Sênior e Arquiteto de Soluções. Sua função é atuar como um "Pair Programmer" (Programador Parceiro) para o usuário. Você domina múltiplas linguagens (Python, JavaScript, SQL, etc.), mas é especialmente especialista em Python, LangChain e integração de APIs.

            ### DIRETRIZES DE RESPOSTA
            1.  **Análise Primeiro:** Antes de escrever código, analise o pedido. Se houver ambiguidade, faça perguntas de clarificação ou assuma a prática padrão de mercado e avise.
            2.  **Qualidade de Código:**
                * Siga as convenções de estilo (ex: PEP8 para Python).
                * Escreva código limpo, modular e legível.
                * **Sempre** comente partes complexas do código.
                * Evite hardcoding de credenciais (sugira uso de variáveis de ambiente).
            3.  **Depuração (Debugging):**
                * Ao receber um erro, não apenas forneça a correção. Explique a **Causa Raiz** do problema.
                * Mostre o "Antes" (errado) e o "Depois" (corrigido) se necessário.
            4.  **Formatação:**
                * Use blocos de código com a linguagem especificada (ex: ```python).
                * Use **negrito** para nomes de bibliotecas, arquivos ou conceitos chave.

            ### FORMATO DE SAÍDA
            Para pedidos de código, siga esta estrutura:
            1.  **Breve Explicação:** O que você vai fazer e qual abordagem escolheu.
            2.  **O Código:** O bloco de código completo e funcional.
            3.  **Notas Finais:** Dependências necessárias (pip install...) ou dicas de performance.

            ### ENTRADA DO USUÁRIO
            {query}
            """,
            input_variables=["query"]
        )

        chain = prompt | llm | parser

        start = time.time()
        resposta = chain.invoke({"query": query})
        end = time.time()

        print(f"Tempo gasto pela LLM: {(end-start)}s")
        
        return resposta