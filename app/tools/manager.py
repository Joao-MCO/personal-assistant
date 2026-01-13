from tools.google_tools import CreateEvent, CheckCalendar
from tools.general import GenericQuestion, RPGQuestion
from tools.news import ReadNews
from tools.codes import CodeHelper
from tools.shark import SharkHelper

news_tool = ReadNews()
generic = GenericQuestion()
code = CodeHelper()
rpg = RPGQuestion()
shark = SharkHelper()
create_event = CreateEvent()
check_calendar = CheckCalendar()

agent_tools = [
    news_tool,
    code,
    generic,
    rpg,
    shark,
    create_event,
    check_calendar
]