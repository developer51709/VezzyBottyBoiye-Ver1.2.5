"""Structured logging with correlation IDs displayed below log messages."""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from colorama import Fore, Style, init as colorama_init

# Initialize colorama
colorama_init(autoreset=True)

# Context variable for correlation ID
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    cid = correlation_id.get()
    if not cid:
        cid = str(uuid.uuid4())
        correlation_id.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set correlation ID in context."""
    correlation_id.set(cid)


def extract_correlation_id(logger: Any, method_name: str, event_dict: dict) -> dict:
    """
    Extract correlation ID and store it under a private key so it doesn't
    appear in the main log message.
    """
    event_dict["_correlation_id"] = get_correlation_id()
    return event_dict


def colorize_event(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Apply color to log level and event message."""
    level = event_dict.get("level", "").upper()

    colors = {
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }

    color = colors.get(level, "")
    event_dict["level"] = f"{color}{level}{Style.RESET_ALL}"

    if "event" in event_dict:
        event_dict["event"] = f"{color}{event_dict['event']}{Style.RESET_ALL}"

    return event_dict


def append_correlation_id(renderer):
    """
    Wrap the renderer so that after rendering the main log message,
    we append the correlation ID on a new line.
    """
    def wrapper(logger, method_name, event_dict):
        cid = event_dict.pop("_correlation_id", None)
        rendered = renderer(logger, method_name, event_dict)

        if cid:
            rendered += (
                f"\n{Fore.MAGENTA}correlation_id="
                f"{Fore.CYAN}{cid}{Style.RESET_ALL}"
            )

        return rendered

    return wrapper


def configure_logging(log_level: str = "INFO", json_output: bool = False) -> None:
    """Configure structlog with optional JSON or colorized console output."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    base_processors = [
        structlog.contextvars.merge_contextvars,
        extract_correlation_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        # JSON output keeps correlation ID inside the JSON
        processors = base_processors + [structlog.processors.JSONRenderer()]
    else:
        # Colorized console output with correlation ID on its own line
        processors = base_processors + [
            colorize_event,
            append_correlation_id(structlog.dev.ConsoleRenderer())
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)