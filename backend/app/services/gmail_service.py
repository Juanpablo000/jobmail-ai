"""
GmailService — Hito 2
Maneja OAuth2 con Gmail y la descarga de correos de ofertas laborales.

Flujo OAuth2:
  1. Usuario visita /auth/login -> se redirige a Google
  2. Google redirige a /auth/callback?code=...
  3. exchange_code() intercambia el código por tokens -> guarda token.json
  4. fetch_job_emails() usa el token para leer correos

Archivos de credenciales (en backend/):
  credentials.json  -> descargado de Google Cloud Console (OAuth2 app)
  token.json        -> autogenerado tras primer login (NO commitear)
"""

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_BACKEND_DIR = Path(__file__).parent.parent.parent
TOKEN_PATH = _BACKEND_DIR / "token.json"
CREDENTIALS_PATH = _BACKEND_DIR / "credentials.json"
VERIFIER_PATH = _BACKEND_DIR / ".oauth_verifier.tmp"


def _get_credentials_path() -> Path:
    """Retorna la ruta al archivo credentials.json (soporta fallback si Windows agregó .json.json)."""
    if CREDENTIALS_PATH.exists():
        return CREDENTIALS_PATH
    double_ext = _BACKEND_DIR / "credentials.json.json"
    if double_ext.exists():
        return double_ext
    return CREDENTIALS_PATH

JOB_SENDERS = {
    "linkedin": [
        "noreply@linkedin.com",
        "jobs-noreply@linkedin.com",
        "jobalerts-noreply@linkedin.com",
        "messaging-digest-noreply@linkedin.com",
    ],
    "computrabajo": [
        "empleos_co@computrabajo.com",
        "noreply@computrabajo.com.co",
        "empleo@computrabajo.com.co",
        "noreply@computrabajo.com",
        "alertas@computrabajo.com.co",
    ],
}


def _build_gmail_query(since_days: int) -> str:
    senders = []
    for platform_senders in JOB_SENDERS.values():
        senders.extend(platform_senders)
    from_clause = " OR ".join(senders)
    return f"from:({from_clause}) newer_than:{since_days}d"


def _detect_platform(from_header: str) -> str:
    from_lower = from_header.lower()
    for platform, senders in JOB_SENDERS.items():
        if any(sender in from_lower for sender in senders):
            return platform
    return "otro"


def _decode_body(payload: dict) -> Optional[str]:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if body_data:
        try:
            decoded = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
            if mime_type == "text/html":
                return decoded
            if mime_type == "text/plain":
                return decoded
        except Exception as e:
            logger.warning(f"Error decodificando body: {e}")
            return None

    parts = payload.get("parts", [])
    html_part = None
    text_part = None

    for part in parts:
        part_mime = part.get("mimeType", "")
        if part_mime == "text/html":
            html_part = _decode_body(part)
        elif part_mime == "text/plain":
            text_part = _decode_body(part)
        elif part_mime.startswith("multipart/"):
            nested = _decode_body(part)
            if nested:
                html_part = html_part or nested

    return html_part or text_part


class GmailService:
    """Servicio para interactuar con la Gmail API v1."""
    _code_verifier: Optional[str] = None

    def get_authorization_url(self) -> str:
        cred_path = _get_credentials_path()
        if not cred_path.exists():
            raise FileNotFoundError(
                f"No se encontró credentials.json en {CREDENTIALS_PATH}.\n"
                "Pasos para obtenerlo:\n"
                "1. Ve a https://console.cloud.google.com\n"
                "2. Crea un proyecto y habilita la Gmail API\n"
                "3. Credenciales -> OAuth2 -> Aplicación web\n"
                "4. URI de redirección: http://localhost:8000/auth/callback\n"
                "5. Descarga el JSON y guárdalo como backend/credentials.json"
            )

        flow = Flow.from_client_secrets_file(
            str(cred_path),
            scopes=SCOPES,
            redirect_uri=settings.google_redirect_uri,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
        # Guardar PKCE code_verifier para el callback
        if hasattr(flow, "code_verifier") and flow.code_verifier:
            self._code_verifier = flow.code_verifier
            try:
                VERIFIER_PATH.write_text(flow.code_verifier)
            except Exception as e:
                logger.warning(f"No se pudo guardar VERIFIER_PATH: {e}")

        logger.info("URL de autorización de Gmail generada")
        return auth_url

    async def exchange_code(self, code: str) -> None:
        cred_path = _get_credentials_path()
        if not cred_path.exists():
            raise FileNotFoundError("credentials.json no encontrado")

        def _exchange():
            flow = Flow.from_client_secrets_file(
                str(cred_path),
                scopes=SCOPES,
                redirect_uri=settings.google_redirect_uri,
            )

            # Recuperar PKCE code_verifier del paso de autorización
            verifier = self._code_verifier
            if not verifier and VERIFIER_PATH.exists():
                try:
                    verifier = VERIFIER_PATH.read_text().strip()
                except Exception:
                    verifier = None

            if verifier:
                flow.code_verifier = verifier

            flow.fetch_token(code=code)
            creds = flow.credentials

            # Limpiar verifier temporal
            if VERIFIER_PATH.exists():
                try:
                    VERIFIER_PATH.unlink(missing_ok=True)
                except Exception:
                    pass
            self._code_verifier = None

            token_data = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else SCOPES,
            }
            TOKEN_PATH.write_text(json.dumps(token_data, indent=2))
            logger.info(f"Token guardado en {TOKEN_PATH}")

        await asyncio.to_thread(_exchange)

    def get_credentials(self) -> Credentials:
        if not TOKEN_PATH.exists():
            raise FileNotFoundError(
                "No hay sesión activa. Visita http://localhost:8000/auth/login "
                "para autenticarte con Gmail."
            )

        token_data = json.loads(TOKEN_PATH.read_text())
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", SCOPES),
        )

        if creds.expired and creds.refresh_token:
            logger.info("Token expirado, refrescando...")
            creds.refresh(Request())
            token_data["token"] = creds.token
            TOKEN_PATH.write_text(json.dumps(token_data, indent=2))
            logger.info("Token refrescado y guardado")

        return creds

    async def fetch_job_emails(self, since_days: int = 7) -> list[dict]:
        creds = self.get_credentials()
        query = _build_gmail_query(since_days)
        logger.info(f"Buscando emails: {query}")

        def _fetch_all():
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            results = []

            response = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=200,
            ).execute()

            messages = response.get("messages", [])
            logger.info(f"Encontrados {len(messages)} mensajes")

            for msg_ref in messages:
                msg_id = msg_ref["id"]
                try:
                    msg = service.users().messages().get(
                        userId="me",
                        id=msg_id,
                        format="full",
                    ).execute()

                    headers = {
                        h["name"].lower(): h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }

                    from_header = headers.get("from", "")
                    platform = _detect_platform(from_header)

                    internal_date_ms = int(msg.get("internalDate", 0))
                    received_at = datetime.fromtimestamp(
                        internal_date_ms / 1000, tz=timezone.utc
                    )

                    html_body = _decode_body(msg.get("payload", {}))
                    if not html_body:
                        logger.warning(f"Mensaje {msg_id} sin body decodificable, omitiendo")
                        continue

                    results.append({
                        "message_id": msg_id,
                        "received_at": received_at,
                        "platform": platform,
                        "html_body": html_body,
                    })

                except HttpError as e:
                    logger.error(f"Error HTTP al obtener mensaje {msg_id}: {e}")
                except Exception as e:
                    logger.error(f"Error inesperado al procesar mensaje {msg_id}: {e}")

            return results

        emails = await asyncio.to_thread(_fetch_all)
        logger.info(f"Procesados {len(emails)} emails con cuerpo válido")
        return emails

    @staticmethod
    def is_authenticated() -> bool:
        return TOKEN_PATH.exists()
