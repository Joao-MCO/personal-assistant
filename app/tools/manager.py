from tools.google_tools import CreateEvent, CheckCalendar
from tools.gmail import CheckEmail, SendEmail
from tools.shark import SharkHelper

# Instâncias para registro no Agente
shark = SharkHelper()
create_event = CreateEvent()
check_calendar = CheckCalendar()
check_email = CheckEmail()
send_email = SendEmail()

agent_tools = [
    shark,
    create_event,
    check_calendar,
    check_email,
    send_email
]