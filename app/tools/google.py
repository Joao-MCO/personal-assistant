import datetime
import uuid
import logging
from typing import Any, Dict, List, Type
from zoneinfo import ZoneInfo
from pydantic import BaseModel, PrivateAttr 
from langchain_core.tools import BaseTool
from services.google import get_service
from models.tools import CheckCalendarInput, CreateEventInput

logger = logging.getLogger(__name__)

# --- Ferramenta 1: Criar Evento ---
class CreateEvent(BaseTool):
    name: str = "CriarEvento"
    description: str = "Use esta ferramenta quando agendar, criar ou marcar NOVAS reuniões no Google Calendar."
    args_schema: Type[BaseModel] = CreateEventInput
    return_direct: bool = False
    
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, meeting_date: Dict[str, Any], description: str, attendees: List[str] = None, meet_length: int = 30, timezone: str = "America/Sao_Paulo"):
        # FIX: Checagem antecipada. Se não tem credencial, nem chama o serviço.
        if not self._user_credentials:
            return "Erro de Permissão: O usuário não está logado no Google Calendar. Peça para ele fazer login na barra lateral."

        service = get_service(self._user_credentials)
        
        if not service:
            return "Erro técnico: Falha ao autenticar no serviço do Google."

        try:
            # Tratamento de Data (Dict ou Objeto)
            if isinstance(meeting_date, dict):
                d = meeting_date
                try:
                    tz = ZoneInfo(timezone)
                except:
                    tz = ZoneInfo("UTC")
                dt_start = datetime.datetime(d['year'], d['month'], d['day'], d['hours'], d['minutes'], tzinfo=tz)
            else:
                dt_start = meeting_date
            
            dt_end = dt_start + datetime.timedelta(minutes=meet_length)

            event = {
                "summary": description,
                "start":{ "dateTime": dt_start.isoformat() },
                "end":{ "dateTime": dt_end.isoformat() },
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": { "type": "hangoutsMeet" }
                    }
                }
            }
            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]

            event_result = service.events().insert(calendarId="primary", body=event, conferenceDataVersion=1).execute()
            link = event_result.get('htmlLink', 'Link indisponível')
            return f"Evento criado com sucesso! Link: {link}"

        except Exception as e:
            return f"Erro técnico ao criar evento: {str(e)}"

# --- Ferramenta 2: Consultar Agenda ---
class CheckCalendar(BaseTool):
    name: str = "ConsultarAgenda"
    description: str = "Verificar disponibilidade e listar compromissos."
    args_schema: Type[BaseModel] = CheckCalendarInput
    return_direct: bool = False
    
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, email: str, start_date: Any, end_date: Any):
        # FIX: Checagem antecipada.
        if not self._user_credentials:
            return "Erro de Permissão: O usuário não está logado no Google Calendar. Peça para ele fazer login na barra lateral."

        service = get_service(self._user_credentials)
        
        if not service:
            return "Erro técnico: Falha ao autenticar no serviço do Google."
        
        try:
            def parse_dt(d):
                if isinstance(d, dict): 
                    return datetime.datetime(d['year'], d['month'], d['day'], d['hours'], d['minutes'])
                return d

            start_dt = parse_dt(start_date).isoformat() + "Z"
            end_dt = parse_dt(end_date).isoformat() + "Z"

            all_events = []
            try:
                events_result = service.events().list(
                    calendarId=email, 
                    timeMin=start_dt, timeMax=end_dt, singleEvents=True, orderBy='startTime'
                ).execute()
                
                items = events_result.get('items', [])
                if not items:
                    return "Nenhum compromisso encontrado nesse período."

                for item in items:
                    start = item['start'].get('dateTime', item['start'].get('date'))
                    summary = item.get('summary', 'Sem título')
                    all_events.append(f"- {start}: {summary}")
            except Exception as e:
                return f"Erro ao ler calendário: {e}"

            return "\n".join(all_events)

        except Exception as e:
            return f"Erro ao consultar: {str(e)}"