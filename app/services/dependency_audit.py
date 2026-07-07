"""
Executa `pip-audit` de verdade (subprocess) contra um requirements.txt
fornecido -- a DETECÇÃO de vulnerabilidades não usa LLM (um LLM "adivinhando"
CVEs de memória seria não-confiável; isso é exatamente o tipo de dado que
deve vir de uma fonte determinística). O LLM entra só depois, na tool
(tools/dev_workflow.py), para resumir os achados em linguagem natural.

Exit code do pip-audit: ele sai com código 1 sempre que encontra QUALQUER
vulnerabilidade (mesmo que seja só em 1 de 50 pacotes) -- não é um "erro" no
sentido de falha de execução. Por isso este módulo interpreta o resultado
pelo conteúdo do JSON, não pelo exit code.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 90


class DependencyAuditError(Exception):
    pass


def run_pip_audit(requirements_txt: str) -> Dict[str, Any]:
    """
    Roda pip-audit contra o conteúdo de requirements.txt fornecido.

    Returns:
        O JSON já parseado, no formato: {"dependencies": [{"name", "version", "vulns": [...]}], "fixes": [...]}

    Raises:
        DependencyAuditError: se o pip-audit não estiver disponível, o
            requirements.txt for inválido, ou a checagem estourar o timeout.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(requirements_txt)
        temp_path = f.name

    try:
        # sys.executable -m pip_audit em vez do binário "pip-audit" solto:
        # garante que roda no MESMO ambiente Python da aplicação (onde
        # pip-audit foi de fato instalado via requirements.txt), em vez de
        # depender de resolução por PATH, que pode não incluir o bin/ do
        # venv dependendo de como o processo foi iniciado.
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--requirement", temp_path, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        raise DependencyAuditError(
            "pip-audit não está instalado no servidor. Adicione 'pip-audit' ao requirements.txt e reinstale as dependências."
        )
    except subprocess.TimeoutExpired:
        raise DependencyAuditError(
            f"A checagem de vulnerabilidades excedeu {TIMEOUT_SECONDS}s (a base de dados pode estar lenta). Tente novamente."
        )
    finally:
        os.unlink(temp_path)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # pip-audit escreve erros reais (requirements.txt malformado, pacote
        # inexistente, etc.) no stderr, sem JSON válido no stdout.
        raise DependencyAuditError(
            f"pip-audit não conseguiu processar o requirements.txt fornecido: {result.stderr.strip()[:500]}"
        )


def summarize_findings(audit_json: Dict[str, Any]) -> str:
    """
    Monta um resumo em texto simples dos achados, pronto para virar o prompt
    do LLM que gera a versão final em linguagem natural (ou para ser
    retornado direto, se não houver nenhuma vulnerabilidade).
    """
    deps_com_vuln = [d for d in audit_json.get("dependencies", []) if d.get("vulns")]

    if not deps_com_vuln:
        total = len(audit_json.get("dependencies", []))
        return f"Nenhuma vulnerabilidade conhecida encontrada em {total} dependência(s) analisada(s)."

    linhas = []
    for dep in deps_com_vuln:
        linhas.append(f"- {dep['name']}=={dep['version']}:")
        for vuln in dep["vulns"]:
            fixes = ", ".join(vuln.get("fix_versions", [])) or "sem correção disponível ainda"
            linhas.append(f"  - {vuln['id']} (correção: {fixes}): {vuln.get('description', '')[:300]}")

    return "\n".join(linhas)