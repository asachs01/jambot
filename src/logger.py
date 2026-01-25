"""Logging configuration for Jambot."""
import logging
import logging.handlers
import os
from src.config import Config


def setup_logger():
    """Configure and return the application logger."""
    # Create logger
    logger = logging.getLogger('jambot')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler (stdout) with simple format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # File handler with rotating logs and detailed format
    # Try to set up file logging, but gracefully degrade if filesystem is read-only
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(Config.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # File logging unavailable (read-only filesystem or no permissions)
        # Log warning to console only
        logger.warning(f"File logging disabled - could not create log file: {e}")

    # Add console handler to logger
    logger.addHandler(console_handler)

    return logger


# Create global logger instance
logger = setup_logger()
