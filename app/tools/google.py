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

    RECURSOS:

    Cria um evento na data/horário especificados.
    Gera automaticamente um link do Google Meet.
    Envia convites se “attendees” (participantes) forem informados.
    """
    args_schema: Type[BaseModel] = CreateEventInput
    return_direct: bool = False

    def _run(self, meeting_date: Dict[str, Any], description: str, attendees: List[str] = None, meet_length: int = 30, timezone: str = "America/Sao_Paulo"):
        logger.info(f"Iniciando solicitação de agendamento: '{description}'")
        logger.debug(f"Parâmetros recebidos: data={meeting_date}, duração={meet_length}min, timezeone={timezone}, participantes={attendees}")

        try:
            service = get_service()
            if not service:
                logger.error("Falha crítica: Serviço do Google Calendar não retornado (autenticação falhou).")
                return {"error": "Falha na autenticação do Google Calendar"}
            
            # Criar objeto de fuso horário
            try:
                tz = ZoneInfo(timezone)
            except Exception as e:
                logger.error(f"Timezone inválido '{timezone}': {e}. Usando UTC como fallback.")
                tz = ZoneInfo("UTC")

            # Construção das datas
            dt_start = datetime.datetime(
                meeting_date.year,
                meeting_date.month,
                meeting_date.day,
                meeting_date.hours,
                meeting_date.minutes,
                tzinfo=tz 
            )
            
            dt_end = dt_start + datetime.timedelta(minutes=meet_length)
            logger.debug(f"Horário calculado (Aware): Início={dt_start}, Fim={dt_end}")

            # Montagem do Payload
            event = {
                "summary": description,
                "start":{
                    "dateTime": dt_start.isoformat(),
                    "timeZone": timezone
                },
                "end":{
                    "dateTime": dt_end.isoformat(),
                    "timeZone": timezone
                },
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": {
                            "type": "hangoutsMeet" 
                        }
                    }
                },
                "reminders":{
                    "useDefault": True
                }
            }
            
            if attendees:
                event["attendees"] = [{"email": email} for email in attendees]
                logger.info(f"Adicionando {len(attendees)} participantes ao evento.")

            logger.debug(f"Payload do evento montado: {event}")

            # Chamada à API do Google
            logger.info("Enviando requisição para Google Calendar API...")
            event_result = service.events().insert(
                calendarId=Settings.google["calendar_id"], 
                body=event, 
                conferenceDataVersion=1
            ).execute()
            
            logger.info(f"Evento criado com sucesso no Google Calendar via API. ID: {event_result.get('id')}")

            # Geração de Resposta com LLM
            logger.info("Iniciando geração de resposta amigável via LLM.")
            
            parser = StrOutputParser()
            llm = ChatGoogleGenerativeAI(
                model=Settings.gemini["model"],
                api_key=Settings.gemini["api_key"]
            )

            prompt = PromptTemplate(
                template="""
                ### PAPEL
                Informar o usuário se deu certo ou não.

                {query}
                """,
                input_variables=["query"]
            )

            chain = prompt | llm | parser

            start = time.time()
            resposta = chain.invoke({"query": event_result})
            end = time.time()

            logger.info(f"Resposta da LLM gerada em {(end-start):.2f}s")
            logger.debug(f"Conteúdo da resposta LLM: {resposta}")
            
            return resposta

        except Exception as e:
            # logger.exception grava automaticamente o stack trace completo do erro
            logger.exception("Ocorreu um erro durante o processo de agendamento.")
            return {"error": str(e)}
        

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