from tools.search import WebSearch
from tools.google_tools import CreateEvent, CheckCalendar
from tools.gmail import CheckEmail, SendEmail
from tools.news import ReadNews
from tools.codes import CodeHelper
from tools.shark import SharkHelper

# Instâncias para registro no Agente
news_tool = ReadNews()
code = CodeHelper()
shark = SharkHelper()
create_event = CreateEvent()
check_calendar = CheckCalendar()
check_email = CheckEmail()
send_email = SendEmail()
search_tool = WebSearch()

agent_tools = [
    news_tool,
    code,
    shark,
    create_event,
    check_calendar,
    check_email,
    send_email,
    search_tool
]