"""
Integração com a API do GitHub para buscar commits recentes de um usuário —
base do GeradorDeStandup. Autenticação via token único (GITHUB_TOKEN, PAT com
escopo de leitura), não OAuth por usuário: é um uso interno de devs que já
sabem gerar seu próprio token, então não há o mesmo motivo para o fluxo mais
pesado que já existe para o Google (onde o usuário final não é técnico).

Duas estratégias de busca:
- Se `repos` for informado, itera o endpoint de commits de cada repositório
  (mais previsível e bem documentado).
- Se não, usa a Search API do GitHub para buscar em toda a organização
  configurada de uma vez (menos previsível — a Search API de commits é mais
  sensível a rate limit — mas necessária para não precisar listar todos os
  repositórios manualmente).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
TIMEOUT_SECONDS = 15


class GitHubError(Exception):
    pass


def _headers() -> Dict[str, str]:
    if not Settings.github_token:
        raise GitHubError(
            "GITHUB_TOKEN não configurado no servidor. Peça para um administrador "
            "gerar um Personal Access Token (escopo 'repo' de leitura) e configurá-lo."
        )
    return {
        "Authorization": f"Bearer {Settings.github_token}",
        "Accept": "application/vnd.github+json, application/vnd.github.cloak-preview+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _since_iso(hours: int) -> str:
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return since.strftime("%Y-%m-%dT%H:%M:%SZ")


def _commits_via_repo_endpoint(username: str, repo: str, since_iso: str) -> List[Dict[str, Any]]:
    url = f"{GITHUB_API}/repos/{repo}/commits"
    params = {"author": username, "since": since_iso, "per_page": 100}
    resp = requests.get(url, headers=_headers(), params=params, timeout=TIMEOUT_SECONDS)
    if resp.status_code == 404:
        logger.warning(f"Repositório '{repo}' não encontrado ou sem acesso — pulando.")
        return []
    resp.raise_for_status()
    commits = resp.json()
    return [
        {
            "repo": repo,
            "message": c["commit"]["message"],
            "date": c["commit"]["author"]["date"],
            "sha": c["sha"][:7],
            "url": c.get("html_url"),
        }
        for c in commits
    ]


def _commits_via_search(username: str, org: str, since_iso: str) -> List[Dict[str, Any]]:
    url = f"{GITHUB_API}/search/commits"
    query = f"author:{username} org:{org} committer-date:>{since_iso}"
    params = {"q": query, "sort": "committer-date", "order": "desc", "per_page": 100}
    resp = requests.get(url, headers=_headers(), params=params, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        {
            "repo": item.get("repository", {}).get("full_name", "?"),
            "message": item["commit"]["message"],
            "date": item["commit"]["author"]["date"],
            "sha": item["sha"][:7],
            "url": item.get("html_url"),
        }
        for item in items
    ]


def fetch_recent_commits(
    username: str,
    since_hours: int = 24,
    repos: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Busca commits recentes de `username`. Levanta GitHubError com uma
    mensagem clara em caso de falha (token ausente, rate limit, etc.) —
    a tool chamadora decide como apresentar isso ao usuário.
    """
    since_iso = _since_iso(since_hours)

    if repos:
        all_commits: List[Dict[str, Any]] = []
        for repo in repos:
            try:
                all_commits.extend(_commits_via_repo_endpoint(username, repo, since_iso))
            except requests.HTTPError as e:
                logger.warning(f"Falha ao buscar commits em '{repo}': {e}")
        return sorted(all_commits, key=lambda c: c["date"], reverse=True)

    if not Settings.github_org:
        raise GitHubError(
            "Nenhum repositório foi informado e GITHUB_ORG não está configurado no "
            "servidor — não é possível buscar em 'toda a organização'. Informe "
            "repositórios específicos (formato 'org/repo') ou configure GITHUB_ORG."
        )

    try:
        return _commits_via_search(username, Settings.github_org, since_iso)
    except requests.HTTPError as e:
        raise GitHubError(f"Falha ao consultar a API de busca do GitHub: {e}")