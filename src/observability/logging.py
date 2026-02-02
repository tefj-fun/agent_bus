"""KAN-70: Structured logging (JSON) for api/worker."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "job_id"):
            log_data["job_id"] = record.job_id

        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id

        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code

        # Module and function info
        log_data["module"] = record.module
        log_data["function"] = record.funcName
        log_data["line"] = record.lineno

        return json.dumps(log_data, default=str)


def setup_logging(
    service_name: str = "agent_bus",
    log_level: str = "INFO",
    json_format: bool = True,
) -> None:
    """Setup structured logging for the application.

    Args:
        service_name: Name of the service (api, worker, orchestrator)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: If True, use JSON format; if False, use standard format
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set service name in all logs
    root_logger = logging.LoggerAdapter(
        root_logger,
        {"service": service_name}
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class RequestLogger:
    """Context manager for request logging with structured fields."""

    def __init__(
        self,
        logger: logging.Logger,
        request_id: str,
        endpoint: str,
        method: str,
        user_id: Optional[str] = None,
    ):
        """Initialize request logger.

        Args:
            logger: Logger instance
            request_id: Unique request ID
            endpoint: API endpoint
            method: HTTP method
            user_id: Optional user ID
        """
        self.logger = logger
        self.request_id = request_id
        self.endpoint = endpoint
        self.method = method
        self.user_id = user_id
        self.start_time = None

    def __enter__(self):
        """Start request timing."""
        import time
        self.start_time = time.time()
        self.logger.info(
            f"{self.method} {self.endpoint}",
            extra={
                "request_id": self.request_id,
                "endpoint": self.endpoint,
                "method": self.method,
                "user_id": self.user_id,
            }
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log request completion."""
        import time
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is None:
            status = "success"
            status_code = 200
        else:
            status = "error"
            status_code = 500

        self.logger.info(
            f"{self.method} {self.endpoint} completed",
            extra={
                "request_id": self.request_id,
                "endpoint": self.endpoint,
                "method": self.method,
                "user_id": self.user_id,
                "duration_ms": duration_ms,
                "status": status,
                "status_code": status_code,
            }
        )
