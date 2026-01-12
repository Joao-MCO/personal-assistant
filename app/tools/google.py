import datetime
import time
import uuid
from typing import Any, Dict, List
from zoneinfo import ZoneInfo
from models.tools import CheckCalendarInput, CreateEventInput
from services.google import get_service
from utils.settings import Settings, logger
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from typing import List, Type, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

class CreateEvent(BaseTool):
    name: str = "CriarEvento"
    description: str = """
    Use esta ferramenta quando agendar, criar ou marcar NOVAS reuniões no Google Calendar.
    NÃO USE PARA: Verificar disponibilidade ou listar eventos existentes.
    """
    args_schema: Type[BaseModel] = CreateEventInput
    return_direct: bool = False

    def _run(self, meeting_date: Dict[str, Any], description: str, attendees: List[str] = None, meet_length: int = 30, timezone: str = "America/Sao_Paulo"):
        logger.info(f"Iniciando solicitação de agendamento: '{description}'")
        logger.debug(f"Parâmetros: data={meeting_date}, dur={meet_length}, tz={timezone}, convidados={attendees}")

        try:
            service = get_service()
            if not service:
                return {"error": "Falha na autenticação do Google Calendar"}
            
            # 1. Tratamento robusto de Timezone
            try:
                tz = ZoneInfo(timezone)
            except Exception as e:
                logger.error(f"Timezone inválido '{timezone}'. Usando UTC.")
                tz = ZoneInfo("UTC")

            # 2. CORREÇÃO CRÍTICA: Normalização de Dicionário/Objeto
            # O LLM envia dict, mas Pydantic pode converter para obj. Aceitamos os dois.
            if isinstance(meeting_date, dict):
                year = meeting_date.get("year")
                month = meeting_date.get("month")
                day = meeting_date.get("day")
                hours = meeting_date.get("hours")
                minutes = meeting_date.get("minutes")
            else:
                year = meeting_date.year
                month = meeting_date.month
                day = meeting_date.day
                hours = meeting_date.hours
                minutes = meeting_date.minutes

            # Construção das datas
            dt_start = datetime.datetime(year, month, day, hours, minutes, tzinfo=tz)
            dt_end = dt_start + datetime.timedelta(minutes=meet_length)

            # Montagem do Payload
            event = {
                "summary": description,
                "start":{ "dateTime": dt_start.isoformat(), "timeZone": timezone },
                "end":{ "dateTime": dt_end.isoformat(), "timeZone": timezone },
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": { "type": "hangoutsMeet" }
                    }
                },
                "reminders":{ "useDefault": True }
            }
            
            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]

            # Chamada à API
            event_result = service.events().insert(
                calendarId=Settings.google["calendar_id"], 
                body=event, 
                conferenceDataVersion=1
            ).execute()
            
            # Resposta Amigável via LLM Interna
            parser = StrOutputParser()
            llm = ChatGoogleGenerativeAI(
                model=Settings.gemini["model"],
                api_key=Settings.gemini["api_key"]
            )

            prompt = PromptTemplate(
                template="""
                ### OBJETIVO
                Analise o JSON de resposta do Google Calendar abaixo e informe ao usuário que o agendamento foi realizado com sucesso.
                Inclua o dia, horário e o link do Google Meet se houver.
                Seja breve e direto (estilo secretária eficiente).

                DADOS DO EVENTO:
                {query}
                """,
                input_variables=["query"]
            )

            chain = prompt | llm | parser
            resposta = chain.invoke({"query": event_result})
            
            return resposta

        except Exception as e:
            logger.exception("Erro no CreateEvent")
            return {"error": f"Erro técnico ao criar evento: {str(e)}"}
        

class CheckCalendar(BaseTool):
    name: str = "ConsultarAgenda"
    description: str = """
    Use essa ferramenta quando verificar disponibilidade, listar compromissos, ver o que está na agenda ou antes de agendar uma reunião, para garantir que não haja conflitos.
    """
    args_schema: Type[BaseModel] = CheckCalendarInput
    return_direct: bool = False

    def _run(self, emails: List[str], start_date: Any, end_date: Any):
        print(emails, start_date, end_date)
        logger.info(f"Consultando agenda: {emails}") # Use logger em vez de print
        
        # Validação de Segurança
        if not emails or not start_date or not end_date:
            return "Erro: Parâmetros de data ou email não foram fornecidos corretamente. Tente reformular a pergunta."

        service = get_service()

        if not service:
            return "Erro: Não foi possível acessar o serviço de agenda."
        
        try:
            tz = ZoneInfo("America/Sao_Paulo")
        except:
            tz = ZoneInfo("UTC")

        if isinstance(start_date, dict):
            year = start_date.get("year")
            month = start_date.get("month")
            day = start_date.get("day")
            hours = start_date.get("hours")
            minutes = start_date.get("minutes")
        else:
            year = start_date.year
            month = start_date.month
            day = start_date.day
            hours = start_date.hours
            minutes = start_date.minutes

        start_dt = datetime.datetime(year, month, day, hours, minutes, tzinfo=tz)
        
        if isinstance(end_date, dict):
            year = end_date.get("year")
            month = end_date.get("month")
            day = end_date.get("day")
            hours = end_date.get("hours")
            minutes = end_date.get("minutes")
        else:
            year = end_date.year
            month = end_date.month
            day = end_date.day
            hours = end_date.hours
            minutes = end_date.minutes

        end_dt = datetime.datetime(year, month, day, hours, minutes, tzinfo=tz)

        try:
            all_events = []
            for email in emails:
                calendar_id = "primary" if email == "primary" else email
                
                event_result = service.events().list(
                    calendarId=calendar_id, 
                    timeMin=start_dt.isoformat(),
                    timeMax=end_dt.isoformat(),
                    singleEvents=True, 
                    orderBy="startTime"
                ).execute()

                items = event_result.get('items', [])
                
                if not items:
                    continue

                for item in items:
                    event_start = item['start'].get('dateTime', item['start'].get('date'))
                    summary = item.get('summary', '(Sem título)')
                    all_events.append(f"- [{event_start}] {summary} ({email})")
            
            if not all_events:
                return "Não encontrei nenhum evento nesse período. Livre! 🏖️"
                
            return "\n".join(all_events)

        except Exception as e:
            logger.error(f"Erro ao listar eventos: {e}")
            return f"Erro ao ler agenda: {str(e)}"