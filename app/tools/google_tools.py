import datetime
import uuid
import logging
from zoneinfo import ZoneInfo
from typing import Any, List, Type
from pydantic import BaseModel, PrivateAttr
from langchain_core.tools import BaseTool

from models.tools import (
    CheckCalendarInput,
    CreateEventInput
)

logger = logging.getLogger(__name__)

MSG_LOGIN = (
    "Pra te mostrar sua agenda eu preciso que você esteja logado no Google Calendar.\n"
    "Por favor, faça login pelo painel lateral e tente novamente."
)

# -------------------------------------------------------------------

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
        meeting_date: dict,
        description: str,
        attendees: List[str] = None,
        meet_length: int = 30,
        timezone: str = "America/Sao_Paulo"
    ):
        logger.info(f"Tool CreateEvent iniciada. Params: {meeting_date}")

        if not self._user_credentials:
            return MSG_LOGIN

        from services.google_services import get_service
        service = get_service(self._user_credentials, "calendar")
        if not service:
            return "Erro técnico ao autenticar no Google Calendar."

        try:
            tz = ZoneInfo(timezone)
            dt_start = datetime.datetime(
                meeting_date["year"],
                meeting_date["month"],
                meeting_date["day"],
                meeting_date.get("hours", 0),
                meeting_date.get("minutes", 0),
                tzinfo=tz
            )

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
                .insert(
                    calendarId="primary",
                    body=event,
                    conferenceDataVersion=1
                )
                .execute()
            )

            link = result.get("htmlLink")
            logger.info(f"Evento criado com sucesso: {link}")
            return f"Evento criado com sucesso! {link}"

        except Exception as e:
            logger.error(f"Erro CreateEvent: {e}", exc_info=True)
            return f"Erro ao criar evento: {e}"

# -------------------------------------------------------------------

class CheckCalendar(BaseTool):
    name: str = "ConsultarAgenda"
    description: str = "Listar compromissos no Google Calendar."
    args_schema: Type[BaseModel] = CheckCalendarInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, email: str, start_date: dict, end_date: dict):
        logger.info(f"Tool CheckCalendar iniciada. Email={email}")

        if not self._user_credentials:
            return MSG_LOGIN

        from services.google_services import get_service
        service = get_service(self._user_credentials, "calendar")
        if not service:
            return "Erro técnico ao autenticar no Google Calendar."

        try:
            def to_dt(d):
                return datetime.datetime(
                    d["year"],
                    d["month"],
                    d["day"],
                    d.get("hours", 0),
                    d.get("minutes", 0),
                    tzinfo=ZoneInfo("UTC"),
                ).isoformat()

            events = (
                service.events()
                .list(
                    calendarId=email,
                    timeMin=to_dt(start_date),
                    timeMax=to_dt(end_date),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
                .get("items", [])
            )

            if not events:
                return "Nenhum compromisso encontrado nesse período."

            output = []
            for ev in events:
                start = ev.get("start", {})
                when = start.get("dateTime") or start.get("date")
                output.append(f"- {when}: {ev.get('summary', 'Sem título')}")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"Erro CheckCalendar: {e}", exc_info=True)
            return f"Erro ao consultar agenda: {e}"

# -------------------------------------------------------------------