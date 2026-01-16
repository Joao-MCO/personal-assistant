import datetime
import uuid
import logging
import base64
from zoneinfo import ZoneInfo
from typing import Any, List, Type
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from pydantic import BaseModel, PrivateAttr
from langchain_core.tools import BaseTool
from models.tools import CheckCalendarInput, CheckEmailInput, CreateEventInput, SendEmailInput

logger = logging.getLogger(__name__)

MSG_LOGIN = (
    "Pra te mostrar sua agenda eu preciso que você esteja logado no Google Calendar.\n"
    "Por favor, faça login pelo painel lateral e tente novamente."
)

class CreateEvent(BaseTool):
    name: str = "CriarEvento"
    description: str = "Criar novos eventos no Google Calendar."
    args_schema: Type[BaseModel] = CreateEventInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, meeting_date: dict, description: str, attendees: List[str] = None, meet_length: int = 30, timezone: str = "America/Sao_Paulo"):
        from services.google_services import get_service
        
        if not self._user_credentials: return MSG_LOGIN
        service = get_service(self._user_credentials, "calendar")
        if not service: return "Erro técnico ao autenticar no Google Calendar."

        try:
            tz = ZoneInfo(timezone)
            # Input agora é garantido como Dict pelo Pydantic, mas mantemos resiliência
            if isinstance(meeting_date, dict):
                dt_start = datetime.datetime(
                    meeting_date["year"], meeting_date["month"], meeting_date["day"],
                    meeting_date.get("hours", 0), meeting_date.get("minutes", 0),
                    tzinfo=tz
                )
            else:
                dt_start = meeting_date # Fallback

            dt_end = dt_start + datetime.timedelta(minutes=meet_length)

            event = {
                "summary": description,
                "start": {"dateTime": dt_start.isoformat()},
                "end": {"dateTime": dt_end.isoformat()},
                "conferenceData": {
                    "createRequest": {"requestId": str(uuid.uuid4()), "conferenceSolutionKey": {"type": "hangoutsMeet"}}
                },
            }
            if attendees: event["attendees"] = [{"email": e} for e in attendees]

            result = service.events().insert(calendarId="primary", body=event, conferenceDataVersion=1).execute()
            return f"Evento criado com sucesso! {result.get('htmlLink')}"
        except Exception as e:
            return f"Erro ao criar evento: {e}"

class CheckCalendar(BaseTool):
    name: str = "ConsultarAgenda"
    description: str = "Listar compromissos no Google Calendar."
    args_schema: Type[BaseModel] = CheckCalendarInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, email: str, start_date: dict, end_date: dict):
        from services.google_services import get_service
        if not self._user_credentials: return MSG_LOGIN
        service = get_service(self._user_credentials, "calendar")
        if not service: return "Erro técnico ao autenticar."

        try:
            def to_dt(d):
                return datetime.datetime(d["year"], d["month"], d["day"], d.get("hours", 0), d.get("minutes", 0), tzinfo=ZoneInfo("UTC"))
            
            start_dt = to_dt(start_date).isoformat()
            end_dt = to_dt(end_date).isoformat()

            events = service.events().list(calendarId=email, timeMin=start_dt, timeMax=end_dt, singleEvents=True, orderBy="startTime").execute().get("items", [])
            
            if not events: return "Nenhum compromisso encontrado nesse período."
            
            output = []
            for event in events:
                start = event.get("start", {})
                when = start.get("dateTime") or start.get("date")
                output.append(f"- {when}: {event.get('summary', 'Sem título')}")
            return "\n".join(output)
        except Exception as e:
            return f"Erro ao consultar agenda: {e}"

class CheckEmail(BaseTool):
    name: str = "ConsultarEmail"
    description: str = "Consultar emails."
    args_schema: Type[BaseModel] = CheckEmailInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds
    
    def _run(self, max_results: int = 5, query: str = None, data_inicio: str = None, data_fim: str = None):
        from services.google_services import get_service
        from datetime import datetime, timedelta

        if not self._user_credentials: return "Usuário não logado."
        service = get_service(self._user_credentials, "gmail")
        
        try:
            filtros = []
            if query: filtros.append(query)
            if data_inicio: filtros.append(f"after:{data_inicio}")
            if data_fim: 
                # Ajuste para incluir o dia final
                try:
                     d_fim = datetime.strptime(data_fim, "%Y/%m/%d") + timedelta(days=1)
                     filtros.append(f"before:{d_fim.strftime('%Y/%m/%d')}")
                except: filtros.append(f"before:{data_fim}")

            q_str = " ".join(filtros)
            results = service.users().messages().list(userId='me', q=q_str, maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            if not messages: return "Nenhum e-mail encontrado."

            emails_completos = []
            for msg in messages:
                detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                headers = detail.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sem Assunto')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconhecido')
                body = self._extract_body(detail.get('payload', {}))
                emails_completos.append(f"De: {sender}\nAssunto: {subject}\nCorpo: {body[:300]}...")
                
            return "\n\n---\n\n".join(emails_completos)
        except Exception as e:
            return f"Erro ao ler emails: {e}"

    def _extract_body(self, payload):
        body_text = ""
        parts = [payload]
        while parts:
            part = parts.pop(0)
            if 'parts' in part:
                parts.extend(part['parts'])
            else:
                data = part.get('body', {}).get('data')
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    if part.get('mimeType') == 'text/plain': return decoded # Prioriza texto puro
                    if part.get('mimeType') == 'text/html': 
                        soup = BeautifulSoup(decoded, 'html.parser')
                        body_text = soup.get_text(separator='\n', strip=True)
        return body_text if body_text else "<Sem conteúdo de texto>"

class SendEmail(BaseTool):
    name: str = "EnviarEmail"
    description: str = "Enviar email."
    args_schema: Type[BaseModel] = SendEmailInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds
    
    def _run(self, to: str, subject: str, body: str, body_type: str ='plain'):
        from services.google_services import get_service
        if not self._user_credentials: return "Usuário não logado."
        service = get_service(self._user_credentials, "gmail")

        try:
            msg = MIMEMultipart()
            msg['to'] = to
            msg['subject'] = subject
            msg.attach(MIMEText(body, body_type))
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            service.users().messages().send(userId='me', body={'raw': raw}).execute()
            return "Email enviado com sucesso."
        except Exception as e:
            return f"Erro ao enviar: {e}"