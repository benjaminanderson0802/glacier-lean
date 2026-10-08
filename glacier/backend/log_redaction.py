"""Logging filters for credentials that could appear in request access records."""
import logging
import re


class RedactWebSocketToken(logging.Filter):
    """Remove WebSocket query credentials from uvicorn access records before formatting."""
    _token_query = re.compile(r"([?&]token=)[^&\s\"']*", re.IGNORECASE)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = self._token_query.sub(r"\1[redacted]", message)
        if redacted != message:
            record.msg, record.args = redacted, ()
        return True
