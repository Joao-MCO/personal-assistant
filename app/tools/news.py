import time
import requests
import json
from typing import Type
from datetime import date, timedelta
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from models.tools import ReadNewsInput
from utils.settings import Settings

class ReadNews(BaseTool):
    name: str = "LerNoticias"
    description: str = """
    Busca notícias atuais usando a API GNews.
    O sistema itera sobre cada tema solicitado para garantir cobertura completa.
    """
    args_schema: Type[BaseModel] = ReadNewsInput
    return_direct: bool = False # False para permitir que o Agente formate o Markdown final

    def _run(self, qtde_noticias: int = 3, assuntos: str = "", pais: str = "br") -> str:
        # Configuração de Datas
        today = date.today()
        start_date = today - timedelta(days=2) # Pega notícias de até 2 dias atrás para garantir frescor
        
        # Definição dos tópicos a buscar
        topicos_padrao = ["general", "world", "nation", "business", "technology", "entertainment", "sports", "science", "health"]
        assuntos_lower = assuntos.lower().strip()
        
        if assuntos_lower in ["all", "geral", "noticias", ""]:
            lista_temas = topicos_padrao
        else:
            lista_temas = [t.strip() for t in assuntos.split(',')]

        print(f"🔎 Buscando GNews para: {lista_temas} ({pais})")
        
        resultados_finais = []
        seen_titles = set() # Deduplicação por título

        for tema in lista_temas:
            try:
                # Lógica de Endpoint (Top Headlines vs Search) do SEU código
                # Se o tema for uma categoria oficial do GNews, usa top-headlines
                if tema in topicos_padrao:
                    url = (
                        f"https://gnews.io/api/v4/top-headlines?category={tema}"
                        f"&max={qtde_noticias}&country={pais}"
                        f"&from={start_date}T00:00:00Z&to={today}T23:59:59Z"
                        f"&apikey={Settings.gnews_api_key}"
                    )
                else:
                    # Se for um termo específico (ex: "Petrobras"), usa search
                    url = (
                        f"https://gnews.io/api/v4/search?q={tema}"
                        f"&max={qtde_noticias}&country={pais}"
                        f"&from={start_date}T00:00:00Z&to={today}T23:59:59Z"
                        f"&sortBy=publishedAt&apikey={Settings.gnews_api_key}"
                    )

                response = requests.get(url)
                data = response.json()
                
                if 'articles' not in data:
                    print(f"Erro API GNews ({tema}): {data}")
                    continue

                tema_buffer = []
                for article in data['articles']:
                    title = article.get('title')
                    if title in seen_titles: continue # Evita duplicatas
                    seen_titles.add(title)

                    desc = article.get('description', '')
                    source = article.get('source', {}).get('name')
                    pub_date = article.get('publishedAt', '')[:10] # Pega só a data YYYY-MM-DD
                    
                    tema_buffer.append(f"- [{pub_date}] {title}\n  Fonte: {source}\n  Resumo: {desc}")

                if tema_buffer:
                    resultados_finais.append(f"\n--- TEMA: {tema.upper()} ---")
                    resultados_finais.extend(tema_buffer)

                # Pausa rápida para não estourar rate limit da API (se for conta free)
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Erro ao buscar {tema}: {e}")

        if not resultados_finais:
            return "Não encontrei notícias recentes. Verifique a API Key ou os termos."

        return "\n".join(resultados_finais)