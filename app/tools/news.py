import time
import requests
import logging
from typing import Type
from datetime import date, timedelta
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from models.tools import ReadNewsInput
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

class ReadNews(BaseTool):
    name: str = "LerNoticias"
    description: str = """
    Busca notícias atuais usando a API GNews.
    O sistema itera sobre cada tema solicitado para garantir cobertura completa.
    """
    args_schema: Type[BaseModel] = ReadNewsInput
    return_direct: bool = False 

    def _run(self, qtde_noticias: int = 3, assuntos: str = "", pais: str = "br") -> str:
        # Log de entrada
        logger.info(f"Tool ReadNews iniciada. Params: qtde_noticias={qtde_noticias}, assuntos='{assuntos}', pais='{pais}'")

        # Configuração de Datas
        today = date.today()
        start_date = today - timedelta(days=2) 
        
        topicos_padrao = ["general", "world", "nation", "business", "technology", "entertainment", "sports", "science", "health"]
        assuntos_lower = assuntos.lower().strip()
        
        if assuntos_lower in ["all", "geral", "noticias", ""]:
            lista_temas = topicos_padrao
        else:
            lista_temas = [t.strip() for t in assuntos.split(',')]

        logger.info(f"GNews Search: Temas={lista_temas} País={pais}")
        
        resultados_finais = []
        seen_titles = set()

        for tema in lista_temas:
            try:
                # Decide endpoint
                endpoint = "top-headlines" if tema in topicos_padrao else "search"
                q_param = f"category={tema}" if endpoint == "top-headlines" else f"q={tema}"
                
                url = (
                    f"https://gnews.io/api/v4/{endpoint}?{q_param}"
                    f"&max={qtde_noticias}&country={pais}"
                    f"&from={start_date}T00:00:00Z&to={today}T23:59:59Z"
                    f"&apikey={Settings.gnews_api_key}"
                )
                
                if endpoint == "search":
                    url += "&sortBy=publishedAt"

                response = requests.get(url)
                data = response.json()
                
                if 'articles' not in data:
                    logger.warning(f"GNews ({tema}): {data.get('errors', 'Sem dados')}")
                    continue

                tema_buffer = []
                for article in data['articles']:
                    title = article.get('title')
                    if title in seen_titles: continue 
                    seen_titles.add(title)

                    desc = article.get('description', '')
                    source = article.get('source', {}).get('name')
                    pub_date = article.get('publishedAt', '')[:10]
                    url_news = article.get('url', '')
                    
                    tema_buffer.append(f"- [{pub_date}] {title}\n  Fonte: {source}\n  Resumo: {desc}\n  Link: {url_news}")

                if tema_buffer:
                    resultados_finais.append(f"\n--- TEMA: {tema.upper()} ---")
                    resultados_finais.extend(tema_buffer)

                time.sleep(0.3) # Rate limit protection
                
            except Exception as e:
                logger.error(f"Erro ao buscar notícias sobre '{tema}': {e}")

        if not resultados_finais:
            logger.info("Nenhuma notícia encontrada com os critérios fornecidos.")
            return "Não encontrei notícias recentes. Verifique a API Key ou os termos."

        return "\n".join(resultados_finais)