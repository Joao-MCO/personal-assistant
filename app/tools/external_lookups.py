"""
Consultas externas sem LLM: CEP, CPF/CNPJ, cotação de moedas e clima.
Todas usam APIs públicas (sem chave), exceto Clima (OpenWeatherMap, precisa
de WEATHER_API_KEY).

Nenhuma dessas chamadas HTTP foi testada contra as APIs reais neste ambiente
-- a rede aqui só libera domínios de pacotes (pypi, npm, etc.), não internet
geral. A estrutura de parsing segue a documentação pública de cada API
(formatos estáveis, de uso comum no Brasil), mas vale um teste manual
contra as APIs de verdade antes de considerar definitivo.
"""

import logging
import time
from typing import ClassVar, Optional, Type

import requests
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from models.tools import (
    ClimaInput,
    ConsultaCEPInput,
    ConsultaDocumentoInput,
    CotacaoMoedaInput,
)
from utils.settings import WrappedSettings as Settings

logger = logging.getLogger(__name__)

TIMEOUT = 10


class ConsultaCEP(BaseTool):
    name: str = "ConsultaCEP"
    description: str = "Use para consultar o endereço (rua, bairro, cidade, UF) a partir de um CEP brasileiro."
    args_schema: Type[BaseModel] = ConsultaCEPInput
    return_direct: bool = False

    def _run(self, cep: str) -> str:
        cep_limpo = "".join(c for c in cep if c.isdigit())
        if len(cep_limpo) != 8:
            return f"CEP inválido: '{cep}' — precisa ter 8 dígitos."

        try:
            resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"ConsultaCEP: erro na requisição: {e}")
            return f"Não consegui consultar o CEP agora: {e}"

        if data.get("erro"):
            return f"CEP {cep} não encontrado."

        return (
            f"{data.get('logradouro', '')}, {data.get('bairro', '')}, "
            f"{data.get('localidade', '')}/{data.get('uf', '')} — CEP {data.get('cep', cep)}"
        )


def _valida_cpf(cpf: str) -> bool:
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def digito(base: str, pesos: list) -> str:
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = digito(cpf[:9], [10, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito(cpf[:9] + d1, [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    return cpf[-2:] == d1 + d2


def _valida_cnpj(cnpj: str) -> bool:
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def digito(base: str, pesos: list) -> str:
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = digito(cnpj[:12], pesos1)
    d2 = digito(cnpj[:12] + d1, pesos2)
    return cnpj[-2:] == d1 + d2


class ConsultaDocumento(BaseTool):
    name: str = "ConsultaDocumento"
    description: str = """
    Use para validar um CPF ou CNPJ (dígito verificador) e, no caso de CNPJ,
    buscar os dados públicos da empresa (razão social, situação cadastral).
    CPF não tem consulta pública de dados no Brasil — só validação.
    """
    args_schema: Type[BaseModel] = ConsultaDocumentoInput
    return_direct: bool = False

    def _run(self, documento: str) -> str:
        limpo = "".join(c for c in documento if c.isdigit())

        if len(limpo) == 11:
            valido = _valida_cpf(limpo)
            return f"CPF {documento}: {'válido' if valido else 'inválido'} (dígito verificador)."

        if len(limpo) == 14:
            valido = _valida_cnpj(limpo)
            if not valido:
                return f"CNPJ {documento}: inválido (dígito verificador)."

            try:
                resp = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{limpo}", timeout=TIMEOUT)
                if resp.status_code == 404:
                    return f"CNPJ {documento}: dígito verificador válido, mas não encontrado na Receita."
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                logger.error(f"ConsultaDocumento (CNPJ): erro na requisição: {e}")
                return f"CNPJ {documento}: dígito verificador válido. Não consegui buscar os dados da empresa agora: {e}"

            razao = data.get("razao_social", "?")
            situacao = data.get("descricao_situacao_cadastral", "?")
            municipio = data.get("municipio", "?")
            uf = data.get("uf", "?")
            return f"CNPJ {documento}: válido. {razao} — {situacao}, {municipio}/{uf}."

        return f"'{documento}' não parece ser um CPF (11 dígitos) nem CNPJ (14 dígitos) válido em formato."


class CotacaoMoeda(BaseTool):
    name: str = "CotacaoMoeda"
    description: str = "Use para consultar a cotação atual de moedas (dólar, euro, bitcoin, libra) em relação ao Real."
    args_schema: Type[BaseModel] = CotacaoMoedaInput
    return_direct: bool = False

    CODIGOS: ClassVar[dict] = {"usd": "USD", "dolar": "USD", "eur": "EUR", "euro": "EUR", "btc": "BTC", "bitcoin": "BTC", "gbp": "GBP", "libra": "GBP"}

    def _run(self, moeda: str = "USD") -> str:
        codigo = self.CODIGOS.get(moeda.strip().lower(), moeda.strip().upper())
        par = f"{codigo}-BRL"

        try:
            resp = requests.get(f"https://economia.awesomeapi.com.br/json/last/{par}", timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"CotacaoMoeda: erro na requisição: {e}")
            return f"Não consegui consultar a cotação agora: {e}"

        chave = f"{codigo}BRL"
        info = data.get(chave)
        if not info:
            return f"Não encontrei cotação para '{moeda}'. Moedas suportadas: dólar, euro, bitcoin, libra."

        return f"{info.get('name', par)}: R$ {float(info['bid']):.2f} (variação do dia: {info.get('pctChange', '?')}%)"


class Clima(BaseTool):
    name: str = "Clima"
    description: str = "Use para consultar o clima atual (temperatura, condição, umidade, vento) de uma cidade."
    args_schema: Type[BaseModel] = ClimaInput
    return_direct: bool = False

    def _run(self, cidade: str) -> str:
        if not Settings.weather_api_key:
            return "A consulta de clima não está configurada no servidor (falta WEATHER_API_KEY)."

        try:
            resp = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": f"{cidade},BR", "appid": Settings.weather_api_key, "units": "metric", "lang": "pt_br"},
                timeout=TIMEOUT,
            )
            if resp.status_code == 404:
                return f"Não encontrei a cidade '{cidade}'."
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"Clima: erro na requisição: {e}")
            return f"Não consegui consultar o clima agora: {e}"

        descricao = data.get("weather", [{}])[0].get("description", "?")
        temp = data.get("main", {}).get("temp")
        sensacao = data.get("main", {}).get("feels_like")
        umidade = data.get("main", {}).get("humidity")
        vento = data.get("wind", {}).get("speed")

        return (
            f"{data.get('name', cidade)}: {descricao}, {temp}°C (sensação de {sensacao}°C), "
            f"umidade {umidade}%, vento {vento} m/s."
        )