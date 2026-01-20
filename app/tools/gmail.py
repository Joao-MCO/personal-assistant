
import logging
import base64
from typing import Any, Type
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from pydantic import BaseModel, PrivateAttr
from langchain_core.tools import BaseTool

from models.tools import (
    CheckEmailInput,
    SendEmailInput
)

logger = logging.getLogger(__name__)

class CheckEmail(BaseTool):
    name: str = "ConsultarEmail"
    description: str = "Consultar emails."
    args_schema: Type[BaseModel] = CheckEmailInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(
        self,
        max_results: int = 5,
        query: str = None,
        data_inicio: str = None,
        data_fim: str = None
    ):
        logger.info("Tool CheckEmail iniciada.")

        if not self._user_credentials:
            return "Usuário não logado."

        from services.google_services import get_service
        service = get_service(self._user_credentials, "gmail")
        if not service:
            return "Erro técnico ao autenticar no Gmail."

        try:
            filtros = []
            if query:
                filtros.append(query)
            if data_inicio:
                filtros.append(f"after:{data_inicio}")
            if data_fim:
                filtros.append(f"before:{data_fim}")

            q = " ".join(filtros)
            results = (
                service.users()
                .messages()
                .list(userId="me", q=q, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return "Nenhum e-mail encontrado."

            emails = []
            for msg in messages:
                detail = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )

                headers = detail.get("payload", {}).get("headers", [])
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "Sem assunto")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "Desconhecido")
                body = self._extract_body(detail.get("payload", {}))

                emails.append(
                    f"De: {sender}\nAssunto: {subject}\nCorpo: {body[:300]}..."
                )

            return "\n\n---\n\n".join(emails)

        except Exception as e:
            logger.error(f"Erro CheckEmail: {e}", exc_info=True)
            return f"Erro ao ler emails: {e}"

    def _extract_body(self, payload):
        parts = [payload]
        while parts:
            part = parts.pop(0)
            if "parts" in part:
                parts.extend(part["parts"])
            else:
                data = part.get("body", {}).get("data")
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    if part.get("mimeType") == "text/plain":
                        return decoded
                    if part.get("mimeType") == "text/html":
                        soup = BeautifulSoup(decoded, "html.parser")
                        return soup.get_text(separator="\n", strip=True)
        return "<Sem conteúdo de texto>"

# -------------------------------------------------------------------

class SendEmail(BaseTool):
    name: str = "EnviarEmail"
    description: str = "Enviar email."
    args_schema: Type[BaseModel] = SendEmailInput
    return_direct: bool = False
    _user_credentials: Any = PrivateAttr(default=None)

    def set_credentials(self, creds):
        self._user_credentials = creds

    def _run(self, to: str, subject: str, body: str, body_type: str = "plain"):
        logger.info("Tool SendEmail iniciada.")

        if not self._user_credentials:
            return "Usuário não logado."

        from services.google_services import get_service
        service = get_service(self._user_credentials, "gmail")
        if not service:
            return "Erro técnico ao autenticar no Gmail."

        try:
            msg = MIMEMultipart()
            msg["to"] = to
            msg["subject"] = subject
            msg.attach(MIMEText(body, body_type))

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            return "Email enviado com sucesso."

        except Exception as e:
            logger.error(f"Erro SendEmail: {e}", exc_info=True)
            return f"Erro ao enviar email: {e}"