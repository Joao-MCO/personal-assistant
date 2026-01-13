from tools.google_tools import CheckEmail, CreateEvent, CheckCalendar
from tools.general import RPGQuestion
from tools.news import ReadNews
from tools.codes import CodeHelper
from tools.shark import SharkHelper

news_tool = ReadNews()
code = CodeHelper()
rpg = RPGQuestion()
shark = SharkHelper()
create_event = CreateEvent()
check_calendar = CheckCalendar()
check_email = CheckEmail()

agent_tools = [
    news_tool,
    code,
    rpg,
    shark,
    create_event,
    check_calendar,
    check_email
]