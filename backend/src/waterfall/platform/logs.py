# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Structured logs, in JSON, one record per line (WF-OBS-0020).

Every record carries its severity, its time, the author of the action and the correlation
identifier bound to the context. A field whose name suggests a secret is removed from the
record, whatever put it there: the logs are not a place a password or a token ends up. The
value of every secret the settings hold is replaced, wherever it shows up in the text of a
record — message, trace, ``repr``. A secret the settings do not know cannot be masked by value.
"""

import json
import logging
import sys
from collections.abc import Callable, Generator, Iterable
from contextlib import contextmanager
from typing import IO, Any, cast

import structlog
from structlog.contextvars import bound_contextvars
from structlog.typing import EventDict, Processor, WrappedLogger

PLATFORM = "platform"
ANONYMOUS = "anonymous"

# Names that suggest a secret: a field whose name contains one of them is dropped.
SECRET_NAMES = ("password", "token", "secret", "authorization", "cookie")


def _is_secret(name: str) -> bool:
    lowered = name.lower()
    return any(word in lowered for word in SECRET_NAMES)


def _without_secrets(value: object) -> object:
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        return {
            key: _without_secrets(item) for key, item in mapping.items() if not _is_secret(str(key))
        }
    if isinstance(value, list | tuple):
        return [_without_secrets(item) for item in cast("list[object]", value)]
    return value


def drop_secrets(_logger: WrappedLogger, _method: str, event: EventDict) -> EventDict:
    """Remove from the record every field whose name evokes a secret, at any depth."""
    return cast("EventDict", _without_secrets(event))


def add_author(_logger: WrappedLogger, _method: str, event: EventDict) -> EventDict:
    """Give the record its author: the platform itself unless the context names someone."""
    event.setdefault("actor", PLATFORM)
    return event


SHARED: list[Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    add_author,
    drop_secrets,
]


MASK = "***"


def mask_values(secrets: Iterable[str]) -> Callable[[Any, str, Any], Any]:
    """Build the last step of the rendering: it hides each secret value in the text written.

    A value is hidden as it is and as JSON writes it, the longest first so that a secret
    which contains another one is hidden whole.
    """
    spellings = {
        text for secret in secrets if secret for text in (secret, json.dumps(secret)[1:-1])
    }
    ordered = sorted(spellings, key=len, reverse=True)

    def mask(_logger: WrappedLogger, _method: str, rendered: Any) -> Any:
        text = str(rendered)
        for spelling in ordered:
            text = text.replace(spelling, MASK)
        return text

    return mask


def configure_logging(
    level: str = "INFO", stream: IO[str] | None = None, secrets: Iterable[str] = ()
) -> None:
    """Send every record — ours and those of the libraries — to ``stream`` as JSON lines.

    ``secrets`` are the values to hide from the text of every record.
    """
    structlog.configure(
        processors=[*SHARED, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[structlog.stdlib.add_logger_name, *SHARED],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            drop_secrets,
            structlog.processors.JSONRenderer(default=repr),
            mask_values(secrets),
        ],
    )
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return the logger of a module."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


@contextmanager
def logging_context(**context: Any) -> Generator[None]:
    """Bind fields — the correlation identifier, the actor — to every record written inside."""
    with bound_contextvars(**context):
        yield
