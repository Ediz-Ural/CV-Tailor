import json
import logging
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

REDACTED = "<redacted>"

_SENSITIVE_KEYS = {
    "access_token",
    "authorization",
    "client_secret",
    "github_token",
    "github_token_encryption_key",
    "jwt_secret",
    "password",
    "parola",
    "secret",
    "token",
}

_TOKEN_PATTERNS = [
    re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]+?\.[A-Za-z0-9_-]+?\.[A-Za-z0-9_-]+?\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(
        r"(?P<prefix>\b(?:access_token|authorization|client_secret|github_token|jwt_secret|password|parola|secret|token)\b\s*[:=]\s*)"
        r"(?P<value>\"[^\"]*\"|'[^']*'|[^\s,}]+)",
        re.IGNORECASE,
    ),
]


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key).lower()
    return any(part in normalized for part in _SENSITIVE_KEYS)


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: REDACTED if _is_sensitive_key(key) else redact_sensitive_data(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, str):
        redacted = value
        for pattern in _TOKEN_PATTERNS:
            if "prefix" in pattern.groupindex:
                redacted = pattern.sub(lambda match: f"{match.group('prefix')}{REDACTED}", redacted)
            else:
                redacted = pattern.sub(REDACTED, redacted)
        return redacted
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return type(value)(redact_sensitive_data(item) for item in value)
    return value


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            try:
                record.msg = redact_sensitive_data(record.getMessage())
                record.args = ()
                return True
            except (TypeError, ValueError):
                record.args = redact_sensitive_data(record.args)
        record.msg = redact_sensitive_data(record.msg)
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        reserved = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                payload[key] = redact_sensitive_data(value)
        return json.dumps(redact_sensitive_data(payload), ensure_ascii=False, default=str)


def configure_sensitive_logging(*, json_logs: bool = True, log_level: str = "INFO") -> None:
    if getattr(logging, "_cv_tailor_sensitive_logging_configured", False):
        return

    original_factory = logging.getLogRecordFactory()
    sensitive_filter = SensitiveDataFilter()

    def redacting_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = original_factory(*args, **kwargs)
        if not record.name.startswith("uvicorn."):
            sensitive_filter.filter(record)
        return record

    logging.setLogRecordFactory(redacting_record_factory)
    setattr(logging, "_cv_tailor_sensitive_logging_configured", True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    if json_logs:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonLogFormatter())
        root_logger.handlers = [handler]
