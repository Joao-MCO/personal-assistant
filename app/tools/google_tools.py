import datetime
import uuid
import logging
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Dict, List, Type
from zoneinfo import ZoneInfo
from pydantic import BaseModel, PrivateAttr
from langchain_core.tools import BaseTool
from models.tools import CheckCalendarInput, CheckEmailInput, CreateEventInput

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
    description: str = "Consultar emails da caixa de entrada;"
    args_schema: Type[BaseModel] = CheckEmailInput
    return_direct: bool = False

    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds
    
    def _run(self, max_results=5):
        from services.google_services import get_service
        import base64

        if not self._user_credentials:
            return "Erro: Usuário não logado."

        service = get_service(self._user_credentials, "gmail")
        if not service:
            return "Erro técnico ao autenticar no Gmail."

        try:
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            
            if not messages:
                return "Nenhum e-mail encontrado na caixa de entrada."

            emails_completos = []

            # 2. Iterar sobre os IDs para buscar o conteúdo real
            for msg in messages:
                # 'format=full' traz o corpo e cabeçalhos
                msg_detail = service.users().messages().get(
                    userId='me', 
                    id=msg['id'], 
                    format='full'
                ).execute()

                payload = msg_detail.get('payload', {})
                headers = payload.get('headers', [])

                # Extrair Assunto e Remetente
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem Assunto')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconhecido')
                
                # Extrair o corpo (usando sua lógica, ajustada para ser método estático ou self)
                body = self._extract_body(payload)

                emails_completos.append(f"De: {sender}\nAssunto: {subject}\nCorpo: {body[:500]}...") # Limitei a 500 chars para não estourar o contexto

            return "\n\n---\n\n".join(emails_completos)

        except Exception as e:
            return f"Erro ao consultar email: {str(e)}"

    def _extract_body(self, payload):
        import base64
        body = '<Conteúdo de texto não disponível>'
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'multipart/alternative':
                    for subpart in part['parts']:
                        if subpart['mimeType'] == "text/plain" and 'data' in subpart['body']:
                            body = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8')
                            break
                elif part['mimeType'] == "text/plain" and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
        return body
