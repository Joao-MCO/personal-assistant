import datetime
import uuid
import logging
from typing import Any, Dict, List, Type
from zoneinfo import ZoneInfo
from pydantic import BaseModel, PrivateAttr
from langchain_core.tools import BaseTool
from models.tools import CheckCalendarInput, CreateEventInput

logger = logging.getLogger(__name__)

# Mensagem padrão para quando o usuário não estiver logado
MSG_LOGIN = (
    "Pra te mostrar sua agenda eu preciso que você esteja logado no Google Calendar.\n"
    "Por favor, faça o seguinte:\n"
    "1. Vá até a barra lateral do painel onde você está usando a Cidinha.\n"
    "2. Clique para conectar / fazer login no Google Calendar com a sua conta.\n"
    "Depois de logar, me manda de novo: 'Minha agenda' ou o período que você quer."
)

# =========================
# Ferramenta: Criar Evento
# =========================
class CreateEvent(BaseTool):
    name: str = "CriarEvento"
    description: str = "Use esta ferramenta quando agendar, criar ou marcar NOVAS reuniões no Google Calendar."
    args_schema: Type[BaseModel] = CreateEventInput
    return_direct: bool = False

    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(
        self,
        meeting_date: Dict[str, Any],
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
            return "Erro técnico: Falha ao autenticar no serviço do Google."

        try:
            if isinstance(meeting_date, dict):
                try:
                    tz = ZoneInfo(timezone)
                except Exception:
                    tz = ZoneInfo("UTC")

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
                event["attendees"] = [{"email": email} for email in attendees]

            result = (
                service.events()
                .insert(calendarId="primary", body=event, conferenceDataVersion=1)
                .execute()
            )

            link = result.get("htmlLink", "Link indisponível")
            return f"Evento criado com sucesso! Link: {link}"

        except Exception as e:
            logger.exception("Erro ao criar evento")
            return f"Erro técnico ao criar evento: {e}"

# =========================
# Ferramenta: Consultar Agenda
# =========================
class CheckCalendar(BaseTool):
    name: str = "ConsultarAgenda"
    description: str = "Verificar disponibilidade e listar compromissos."
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
            return "Erro técnico: Falha ao autenticar no serviço do Google."

        try:
            def parse_dt(d):
                if isinstance(d, dict):
                    return datetime.datetime(
                        d["year"],
                        d["month"],
                        d["day"],
                        d.get("hours", 0),
                        d.get("minutes", 0),
                        tzinfo=ZoneInfo("UTC"),
                    )
                return d

            start_dt = parse_dt(start_date).isoformat()
            end_dt = parse_dt(end_date).isoformat()

            events_result = (
                service.events()
                .list(
                    calendarId=email,
                    timeMin=start_dt,
                    timeMax=end_dt,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            items = events_result.get("items", [])
            if not items:
                return "Nenhum compromisso encontrado nesse período."

            all_events = []

            for item in items:
                start_info = item.get("start", {})
                summary = item.get("summary", "Sem título")

                # 🔴 CORREÇÃO DEFINITIVA AQUI
                if "dateTime" in start_info:
                    start_str = start_info["dateTime"]
                else:
                    start_str = start_info.get("date")

                all_events.append(f"- {start_str}: {summary}")

            return "\n".join(all_events)

        except Exception as e:
            logger.exception("Erro ao consultar agenda")
            return f"Erro ao consultar agenda: {e}"
