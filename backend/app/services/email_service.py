"""
AeroGuard — Email Service (RF-003)
Gestión de envío de correos (recuperación de contraseña, notificaciones).
En modo desarrollo o sin SMTP configurado, simula el envío registrándolo en log.
"""

import logging
from app.core.config import settings

logger = logging.getLogger("aeroguard.email")


async def send_reset_email(email: str, token: str) -> bool:
    """
    Envía enlace de recuperación de contraseña.
    En entorno académico o sin SMTP configurado, registra el enlace directamente en logs.
    """
    reset_url = f"http://localhost:3000/#reset-password?token={token}"

    logger.info(f"[EMAIL SIMULATION] Enlace de recuperación para {email}: {reset_url}")
    print(f"\n[AEROGUARD EMAIL SERVICE] Para: {email}\nEnlace de recuperación: {reset_url}\n")

    # Si se han configurado credenciales SMTP válidas
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = settings.FROM_EMAIL
            msg["To"] = email
            msg["Subject"] = "AeroGuard — Recuperación de Contraseña"

            body = f"""Hola,

Has solicitado restablecer tu contraseña en AeroGuard.
Haz clic en el siguiente enlace (válido por {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutos):

{reset_url}

Si no realizaste esta solicitud, ignora este mensaje.
"""
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as exc:
            logger.error(f"Error enviando correo SMTP a {email}: {exc}")
            return False

    return True
