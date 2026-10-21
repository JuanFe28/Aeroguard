"""Evita que los logs de acceso conserven tokens de la negociación WebSocket."""
import logging
import re


class RedactCredentials(logging.Filter):
    def filter(self, record):
        def redact(value):
            if not isinstance(value, str):
                return value
            value = re.sub(r'([?&]token=)[^\s"\']+', r'\1[REDACTED]', value)
            return re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[JWT_REDACTED]', value)
        record.msg = redact(record.msg)
        if isinstance(record.args, dict):
            record.args = {key: redact(value) for key, value in record.args.items()}
        else:
            record.args = tuple(redact(value) for value in record.args)
        return True


def install_log_redaction():
    for name in ('uvicorn.error', 'uvicorn.access'):
        logger = logging.getLogger(name)
        if not any(isinstance(item, RedactCredentials) for item in logger.filters):
            logger.addFilter(RedactCredentials())
