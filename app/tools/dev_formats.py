"""
Utilitários de desenvolvimento, todos sem LLM: conversão entre formatos de
dado, codificação/decodificação, geração de identificadores únicos, hash,
senha/token e dados fictícios para teste.
"""

import base64
import csv
import hashlib
import io
import json
import logging
import secrets
import string
import urllib.parse
from typing import ClassVar, List, Optional, Type

import yaml
from faker import Faker
from langchain_core.tools import BaseTool
from nanoid import generate as nanoid_generate
from pydantic import BaseModel
from ulid import ULID

from models.tools import (
    CodificadorInput,
    ConversorDeFormatoInput,
    GeradorDeDadosFakeInput,
    GeradorDeHashInput,
    GeradorDeIdentificadorInput,
    GeradorDeSenhaInput,
)

logger = logging.getLogger(__name__)

_fake = Faker("pt_BR")


# ---------------------------------------------------------------------------
# Conversão JSON / YAML / CSV
# ---------------------------------------------------------------------------

def _parse_csv(texto: str) -> list:
    reader = csv.DictReader(io.StringIO(texto))
    return [dict(row) for row in reader]


def _to_csv(dados: list) -> str:
    if not dados:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(dados[0].keys()))
    writer.writeheader()
    writer.writerows(dados)
    return output.getvalue()


class ConversorDeFormato(BaseTool):
    name: str = "ConversorDeFormato"
    description: str = "Use para validar, formatar ou converter dados entre JSON, YAML e CSV."
    args_schema: Type[BaseModel] = ConversorDeFormatoInput
    return_direct: bool = False

    def _run(self, conteudo: str, origem: str, destino: str) -> str:
        try:
            if origem == "json":
                dados = json.loads(conteudo)
            elif origem == "yaml":
                dados = yaml.safe_load(conteudo)
            elif origem == "csv":
                dados = _parse_csv(conteudo)
            else:
                return f"Formato de origem desconhecido: '{origem}'."
        except Exception as e:
            return f"Não consegui interpretar o conteúdo como {origem.upper()}: {e}"

        try:
            if destino == "json":
                return json.dumps(dados, indent=2, ensure_ascii=False)
            if destino == "yaml":
                return yaml.dump(dados, allow_unicode=True, sort_keys=False)
            if destino == "csv":
                if isinstance(dados, dict):
                    dados = [dados]
                return _to_csv(dados)
            return f"Formato de destino desconhecido: '{destino}'."
        except Exception as e:
            return f"Consegui ler o {origem.upper()}, mas não converter para {destino.upper()}: {e}"


# ---------------------------------------------------------------------------
# Codificação / Decodificação
# ---------------------------------------------------------------------------

class Codificador(BaseTool):
    name: str = "Codificador"
    description: str = "Use para codificar ou decodificar texto em Base64, URL encoding ou Hexadecimal."
    args_schema: Type[BaseModel] = CodificadorInput
    return_direct: bool = False

    def _run(self, texto: str, operacao: str) -> str:
        try:
            if operacao == "base64_encode":
                return base64.b64encode(texto.encode("utf-8")).decode("ascii")
            if operacao == "base64_decode":
                return base64.b64decode(texto.encode("ascii")).decode("utf-8")
            if operacao == "url_encode":
                return urllib.parse.quote(texto)
            if operacao == "url_decode":
                return urllib.parse.unquote(texto)
            if operacao == "hex_encode":
                return texto.encode("utf-8").hex()
            if operacao == "hex_decode":
                return bytes.fromhex(texto).decode("utf-8")
            return f"Operação desconhecida: '{operacao}'."
        except Exception as e:
            return f"Não consegui {operacao.replace('_', ' ')}: {e}. Confira se o texto está no formato esperado para essa operação."


# ---------------------------------------------------------------------------
# Identificadores únicos
# ---------------------------------------------------------------------------

class GeradorDeIdentificador(BaseTool):
    name: str = "GeradorDeIdentificador"
    description: str = "Use para gerar identificadores únicos: UUID v4, ULID ou NanoID."
    args_schema: Type[BaseModel] = GeradorDeIdentificadorInput
    return_direct: bool = False

    def _run(self, tipo: str = "uuid4", quantidade: int = 1) -> str:
        import uuid as uuid_lib

        quantidade = max(1, min(quantidade, 50))
        geradores = {
            "uuid4": lambda: str(uuid_lib.uuid4()),
            "ulid": lambda: str(ULID()),
            "nanoid": lambda: nanoid_generate(),
        }
        gerador = geradores.get(tipo)
        if gerador is None:
            return f"Tipo desconhecido: '{tipo}'. Use uuid4, ulid ou nanoid."

        return "\n".join(gerador() for _ in range(quantidade))


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

class GeradorDeHash(BaseTool):
    name: str = "GeradorDeHash"
    description: str = "Use para calcular o hash (MD5, SHA1, SHA256 ou SHA512) de um texto."
    args_schema: Type[BaseModel] = GeradorDeHashInput
    return_direct: bool = False

    ALGORITMOS: ClassVar[dict] = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}

    def _run(self, texto: str, algoritmo: str = "sha256") -> str:
        func = self.ALGORITMOS.get(algoritmo)
        if func is None:
            return f"Algoritmo desconhecido: '{algoritmo}'."
        return func(texto.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Senha / Token
# ---------------------------------------------------------------------------

_PALAVRAS_MEMORAVEIS = [
    "tigre", "monte", "rio", "sol", "lua", "verde", "azul", "porto", "vento", "pedra",
    "onda", "campo", "flor", "nuvem", "trovao", "raio", "folha", "praia", "ilha", "torre",
]


class GeradorDeSenha(BaseTool):
    name: str = "GeradorDeSenha"
    description: str = "Use para gerar uma senha ou token seguro: forte (letras/números/símbolos), numérica (tipo PIN) ou memorável (palavras)."
    args_schema: Type[BaseModel] = GeradorDeSenhaInput
    return_direct: bool = False

    def _run(self, tamanho: int = 16, modo: str = "forte") -> str:
        tamanho = max(4, min(tamanho, 128))

        if modo == "numerica":
            return "".join(secrets.choice(string.digits) for _ in range(tamanho))

        if modo == "memoravel":
            palavras = [secrets.choice(_PALAVRAS_MEMORAVEIS) for _ in range(4)]
            return "-".join(palavras) + "-" + "".join(secrets.choice(string.digits) for _ in range(2))

        alfabeto = string.ascii_letters + string.digits + "!@#$%&*-_="
        return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


# ---------------------------------------------------------------------------
# Dados fictícios / Lorem Ipsum
# ---------------------------------------------------------------------------

class GeradorDeDadosFake(BaseTool):
    name: str = "GeradorDeDadosFake"
    description: str = "Use para gerar dados fictícios para teste: nome, telefone, email, empresa, endereço, CPF (formato válido, mas falso) ou texto lorem ipsum."
    args_schema: Type[BaseModel] = GeradorDeDadosFakeInput
    return_direct: bool = False

    def _run(self, tipo: str, quantidade: int = 1) -> str:
        quantidade = max(1, min(quantidade, 20))
        geradores = {
            "nome": _fake.name,
            "telefone": _fake.phone_number,
            "email": _fake.email,
            "empresa": _fake.company,
            "endereco": lambda: _fake.address().replace("\n", ", "),
            "cpf": _fake.cpf,
            "texto": lambda: _fake.paragraph(nb_sentences=4),
        }
        gerador = geradores.get(tipo)
        if gerador is None:
            return f"Tipo desconhecido: '{tipo}'."

        return "\n".join(gerador() for _ in range(quantidade))