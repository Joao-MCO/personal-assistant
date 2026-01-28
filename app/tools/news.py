import time
import requests
import logging
from typing import Type
from datetime import date, timedelta
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from duckduckgo_search import DDGS
from models.tools import ReadNewsInput
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

class ReadNews(BaseTool):
    name: str = "LerNoticias"
    description: str = """
    Busca notícias e atualizações recentes (Híbrido: GNews + Busca Web Recente).
    Use para: Notícias gerais, Esportes (BID, contratações), Mercado e Lançamentos.
    Aceita operadores de busca (ex: 'site:ge.globo.com').
    """
    args_schema: Type[BaseModel] = ReadNewsInput
    return_direct: bool = False 

    def _run(self, qtde_noticias: int = 3, assuntos: str = "", pais: str = "br") -> str:
        logger.info(f"Tool ReadNews iniciada. Params: qtde={qtde_noticias}, assuntos='{assuntos}'")

        # Configuração de Datas para GNews
        today = date.today()
        start_date = today - timedelta(days=2) 
        
        topicos_padrao = ["general", "world", "nation", "business", "technology", "entertainment", "sports", "science", "health"]
        assuntos_lower = assuntos.lower().strip()
        
        if assuntos_lower in ["all", "geral", "noticias", ""]:
            lista_temas = topicos_padrao
        else:
            lista_temas = [t.strip() for t in assuntos.split(',')]

        resultados_finais = []
        seen_titles = set()
        
        # Mapeamento de região para o DuckDuckGo (ex: 'br-pt' para resultados do Brasil)
        ddg_region_map = {"br": "br-pt", "us": "us-en", "pt": "pt-pt"}
        ddg_region = ddg_region_map.get(pais, "wt-wt")

        for tema in lista_temas:
            tema_buffer = []
            
            # --- 1. Tenta GNews (Apenas para temas genéricos/manchetes) ---
            # Se a busca contiver "site:" ou for muito específica, pule o GNews pois ele falhará.
            use_gnews = True
            if "site:" in tema or "BID" in tema.upper():
                use_gnews = False

            if use_gnews and Settings.gnews_api_key:
                try:
                    endpoint = "top-headlines" if tema in topicos_padrao else "search"
                    q_param = f"category={tema}" if endpoint == "top-headlines" else f"q={tema}"
                    
                    url = (
                        f"https://gnews.io/api/v4/{endpoint}?{q_param}"
                        f"&max={qtde_noticias}&country={pais}"
                        f"&from={start_date}T00:00:00Z&to={today}T23:59:59Z"
                        f"&apikey={Settings.gnews_api_key}"
                    )
                    if endpoint == "search": url += "&sortBy=publishedAt"

                    response = requests.get(url, timeout=4)
                    data = response.json()
                    if 'articles' in data:
                        for article in data['articles']:
                            self._process_article(article, seen_titles, tema_buffer, "GNews")
                except Exception as e:
                    logger.warning(f"GNews ignorado/falhou para '{tema}': {e}")

            # --- 2. Tenta DuckDuckGo TEXT Search (Com filtro de tempo) ---
            # Aqui está o segredo: usamos .text() em vez de .news()
            # timelimit='w' = última semana (garante frescor, mas pega indexação do site)
            # timelimit='d' = último dia (pode ser muito restritivo se a notícia for de ontem à noite)
            
            if len(tema_buffer) < qtde_noticias:
                missing = qtde_noticias - len(tema_buffer)
                logger.info(f"Buscando '{tema}' no DuckDuckGo (Web Recente)...")
                
                try:
                    with DDGS() as ddgs:
                        # .text permite operadores como site: e filetype:
                        ddg_results = list(ddgs.text(
                            keywords=tema, 
                            region=ddg_region, 
                            safesearch='off', 
                            timelimit='w', # <--- O PULO DO GATO: Filtra resultados da última semana
                            max_results=missing + 3
                        ))
                        
                        for res in ddg_results:
                            # Normaliza para o formato de notícia
                            article_std = {
                                'title': res.get('title'),
                                'description': res.get('body'),
                                'source': {'name': 'Web Search'}, # DDG Text não retorna 'source' estruturado
                                'publishedAt': 'Semana Recente', 
                                'url': res.get('href')
                            }
                            self._process_article(article_std, seen_titles, tema_buffer, "WebRecente")
                            
                            if len(tema_buffer) >= qtde_noticias:
                                break
                except Exception as e:
                    logger.error(f"DDG Web Recente falhou: {e}")

            if tema_buffer:
                resultados_finais.append(f"\n--- TEMA: {tema.upper()} ---")
                resultados_finais.extend(tema_buffer)
            
            time.sleep(0.5)

        if not resultados_finais:
            return "Não encontrei informações recentes. Tente refinar a busca."

        return "\n".join(resultados_finais)

    def _process_article(self, article, seen_titles, buffer, source_engine):
        title = article.get('title')
        if not title: return
        
        # Deduplicação simples
        if title in seen_titles: return
        seen_titles.add(title)

        desc = article.get('description', 'Ver link.')
        source = article.get('source', {}).get('name', 'Fonte Web')
        pub_date = article.get('publishedAt', '')[:10]
        url = article.get('url', '')

        buffer.append(
            f"- {title}\n"
            f"  Fonte: {source} ({source_engine}) | Data: {pub_date}\n"
            f"  Resumo: {desc}\n"
            f"  Link: {url}"
        )