import datetime
import uuid
import logging
from typing import Any, Dict, List, Type
from zoneinfo import ZoneInfo
from pydantic import BaseModel, PrivateAttr
from langchain_core.tools import BaseTool
from models.tools import CheckCalendarInput, CreateEventInput

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
