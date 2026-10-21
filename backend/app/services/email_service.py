"""
AeroGuard — Email Service (RF-003)
Gestión de envío de correos (recuperación de contraseña, notificaciones).
Sin SMTP configurado informa falta de entrega sin divulgar enlaces ni tokens.
"""

import logging
from app.core.config import settings

logger = logging.getLogger("aeroguard.email")


async def send_reset_email(email: str, token: str) -> bool:
    """
    Envía enlace de recuperación de contraseña.
    Devuelve False si SMTP no está configurado o no pudo entregar el correo.
    """
    reset_url = f"{settings.PUBLIC_FRONTEND_URL.rstrip('/')}/#/reset-password?token={token}"
    # Los tokens nunca se imprimen: tampoco en desarrollo ni cuando falla SMTP.

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
            logger.error("No se pudo entregar el correo de recuperación")
            return False

    logger.warning("Recuperación no entregada: SMTP no configurado")
    return False
