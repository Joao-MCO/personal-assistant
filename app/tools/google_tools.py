import datetime
import uuid
import logging
import os
import base64
from bs4 import BeautifulSoup
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Dict, List, Type
from zoneinfo import ZoneInfo
from pydantic import BaseModel, PrivateAttr
from langchain_core.tools import BaseTool
import requests
from models.tools import CheckCalendarInput, CheckEmailInput, CreateEventInput, SendEmailInput

logger = logging.getLogger(__name__)

MSG_LOGIN = (
    "Pra te mostrar sua agenda eu preciso que você esteja logado no Google Calendar.\n"
    "Por favor, faça login pelo painel lateral e tente novamente."
)

# =========================
# Criar Evento
# =========================
class CreateEvent(BaseTool):
    name: str = "CriarEvento"
    description: str = "Criar novos eventos no Google Calendar."
    args_schema: Type[BaseModel] = CreateEventInput
    return_direct: bool = False

    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(
        self,
        meeting_date: Any,
        description: str,
        attendees: List[str] = None,
        meet_length: int = 30,
        timezone: str = "America/Sao_Paulo",
    ):
        from services.google_services import get_service

        if not self._user_credentials:
            return MSG_LOGIN

        service = get_service(self._user_credentials)
        if not service:
            return "Erro técnico ao autenticar no Google Calendar."

        try:
            tz = ZoneInfo(timezone)

            # ✔ Aceita dict, DateParts ou datetime
            if hasattr(meeting_date, "year"):
                dt_start = datetime.datetime(
                    meeting_date.year,
                    meeting_date.month,
                    meeting_date.day,
                    getattr(meeting_date, "hours", 0) or 0,
                    getattr(meeting_date, "minutes", 0) or 0,
                    tzinfo=tz,
                )
            elif isinstance(meeting_date, dict):
                dt_start = datetime.datetime(
                    meeting_date["year"],
                    meeting_date["month"],
                    meeting_date["day"],
                    meeting_date.get("hours", 0),
                    meeting_date.get("minutes", 0),
                    tzinfo=tz,
                )
            else:
                dt_start = meeting_date

            dt_end = dt_start + datetime.timedelta(minutes=meet_length)

            event = {
                "summary": description,
                "start": {"dateTime": dt_start.isoformat()},
                "end": {"dateTime": dt_end.isoformat()},
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            }

            if attendees:
                event["attendees"] = [{"email": e} for e in attendees]

            result = (
                service.events()
                .insert(calendarId="primary", body=event, conferenceDataVersion=1)
                .execute()
            )

            return f"Evento criado com sucesso! {result.get('htmlLink')}"

        except Exception as e:
            logger.exception("Erro ao criar evento")
            return f"Erro ao criar evento: {e}"

# =========================
# Consultar Agenda
# =========================
class CheckCalendar(BaseTool):
    name: str = "ConsultarAgenda"
    description: str = "Listar compromissos no Google Calendar."
    args_schema: Type[BaseModel] = CheckCalendarInput
    return_direct: bool = False

    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, email: str, start_date: Any, end_date: Any):
        from services.google_services import get_service

        if not self._user_credentials:
            return MSG_LOGIN

        service = get_service(self._user_credentials)
        if not service:
            return "Erro técnico ao autenticar no Google Calendar."

        try:
            def to_datetime(d):
                # ✔ DateParts (Pydantic)
                if hasattr(d, "year"):
                    return datetime.datetime(
                        d.year,
                        d.month,
                        d.day,
                        getattr(d, "hours", 0) or 0,
                        getattr(d, "minutes", 0) or 0,
                        tzinfo=ZoneInfo("UTC"),
                    )

                # ✔ dict
                if isinstance(d, dict):
                    return datetime.datetime(
                        d["year"],
                        d["month"],
                        d["day"],
                        d.get("hours", 0),
                        d.get("minutes", 0),
                        tzinfo=ZoneInfo("UTC"),
                    )

                # ✔ datetime
                return d

            start_dt = to_datetime(start_date).isoformat()
            end_dt = to_datetime(end_date).isoformat()

            events = (
                service.events()
                .list(
                    calendarId=email,
                    timeMin=start_dt,
                    timeMax=end_dt,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
                .get("items", [])
            )

            if not events:
                return "Nenhum compromisso encontrado nesse período."

            output = []

            for event in events:
                start = event.get("start", {})
                summary = event.get("summary", "Sem título")

                # ✔ dateTime ou date
                when = start.get("dateTime") or start.get("date")
                output.append(f"- {when}: {summary}")

            return "\n".join(output)

        except Exception as e:
            logger.exception("Erro ao consultar agenda")
            return f"Erro ao consultar agenda: {e}"

class CheckEmail(BaseTool):
    name: str = "ConsultarEmail"
    description: str = "Consultar emails da caixa de entrada com filtros opcionais de data e texto."
    args_schema: Type[BaseModel] = CheckEmailInput
    return_direct: bool = False

    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds
    
    def _run(self, max_results: int = 5, query: str = None, data_inicio: str = None, data_fim: str = None):
        from services.google_services import get_service
        from datetime import datetime, timedelta # Importação necessária para corrigir a data

        if not self._user_credentials:
            return "Erro: Usuário não logado."

        service = get_service(self._user_credentials, "gmail")
        if not service:
            return "Erro técnico ao autenticar no Gmail."

        try:
            filtros = []
            
            # --- Correção Inteligente de Datas ---
            # Se o LLM mandar a mesma data para inicio e fim (ex: buscar emails "do dia 13"),
            # o Gmail retornaria vazio pois 'before' é exclusivo.
            # Aqui nós empurramos o 'before' para o dia seguinte automaticamente.
            if data_inicio and data_fim and data_inicio == data_fim:
                try:
                    # Tenta converter para somar 1 dia
                    dt_fim = datetime.strptime(data_fim, "%Y/%m/%d")
                    dt_fim_ajustada = dt_fim + timedelta(days=1)
                    data_fim = dt_fim_ajustada.strftime("%Y/%m/%d")
                except ValueError:
                    pass # Se formato estiver errado, segue o padrão sem crashar

            # 1. Filtro por palavra-chave
            if query:
                # Removemos as aspas duplas forçadas para tornar a busca mais flexível
                # (ex: achar "the news" mesmo se o sender for "the news ☕")
                filtros.append(f'{query}') 
            
            # 2. Filtros de Data
            if data_inicio:
                filtros.append(f"after:{data_inicio}")
            
            if data_fim:
                filtros.append(f"before:{data_fim}")

            query_string = " ".join(filtros) if filtros else None

            # --- Chamada da API ---
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q=query_string, 
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            
            if not messages:
                msg_retorno = "Nenhum e-mail encontrado na caixa de entrada"
                if query_string:
                    msg_retorno += f" com os filtros: {query_string}"
                return msg_retorno + "."

            emails_completos = []

            for msg in messages:
                msg_detail = service.users().messages().get(
                    userId='me', 
                    id=msg['id'], 
                    format='full'
                ).execute()

                payload = msg_detail.get('payload', {})
                headers = payload.get('headers', [])

                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem Assunto')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconhecido')
                body = self._extract_body(payload)

                emails_completos.append(f"De: {sender}\nAssunto: {subject}\nCorpo: {body[:500]}...") 

            return "\n\n---\n\n".join(emails_completos)

        except Exception as e:
            return f"Erro ao consultar email: {str(e)}"

    def _extract_body(self, payload):
        import base64
        from bs4 import BeautifulSoup
        
        body_text = '<Conteúdo de texto não disponível>'
        plain_text = None
        html_text = None

        # Função auxiliar para decodificar
        def decode_data(data):
            if not data: return None
            return base64.urlsafe_b64decode(data).decode('utf-8')

        # Lista plana para facilitar a busca (caso haja aninhamento de parts)
        parts_queue = [payload]
        
        while parts_queue:
            part = parts_queue.pop(0)
            
            # Se tiver sub-partes, adiciona na fila para processar
            if 'parts' in part:
                parts_queue.extend(part['parts'])
                continue

            mime_type = part.get('mimeType')
            body_data = part.get('body', {}).get('data')

            if not body_data:
                continue

            decoded_text = decode_data(body_data)

            if mime_type == 'text/plain':
                plain_text = decoded_text
            elif mime_type == 'text/html':
                html_text = decoded_text

        # LÓGICA DE PRIORIDADE:
        # 1. Se tiver texto puro, usamos ele (é mais limpo para LLMs).
        # 2. Se não tiver, tentamos converter o HTML para texto.
        if plain_text:
            body_text = plain_text
        elif html_text:
            # Usa BeautifulSoup para extrair texto do HTML
            soup = BeautifulSoup(html_text, 'html.parser')
            # separator='\n' garante que títulos e parágrafos não fiquem colados
            body_text = soup.get_text(separator='\n', strip=True)
            
            # (Opcional) Tentar pegar links de imagens se for muito importante
            # images = [img['src'] for img in soup.find_all('img', src=True)]
            # if images: body_text += "\n\n[Imagens encontradas]: " + ", ".join(images)

        return body_text

class SendEmail(BaseTool):
    name: str = "EnviarEmail"
    description: str = "Enviar email para outra pessoa."
    args_schema: Type[BaseModel] = SendEmailInput
    return_direct: bool = False

    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds
    
    def _run(self,  to: str, subject: str, body: str, body_type: str ='plain'):
        from services.google_services import get_service

        if not self._user_credentials:
            return "Erro: Usuário não logado."

        service = get_service(self._user_credentials, "gmail")
        if not service:
            return "Erro técnico ao autenticar no Gmail."

        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject

            if body_type.lower() not in ['plain', 'html']:
                raise ValueError('body_type deve ser `plain` ou `html`')
            
            message.attach(MIMEText(body, body_type.lower()))

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            sent_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return sent_message
        except Exception as e:
            return f"Erro ao consultar email: {str(e)}"

    