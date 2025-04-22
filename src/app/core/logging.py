import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_level=logging.INFO, enable_file_logging=True):
    """
    Configure application-wide logging with both console and file handlers.
    
    Args:
        log_level: The minimum log level to capture
        enable_file_logging: Whether to log to files in addition to console
    """
    # Create logs directory if it doesn't exist
    if enable_file_logging:
        logs_dir = Path(__file__).parents[2] / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / "app.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates when reloading in dev
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    verbose_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (with color if possible)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if enable_file_logging:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(verbose_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific log levels for noisy modules
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.INFO)
    
    # Return the root logger
    return root_logger

def get_logger(name):
    """
    Get a logger for a specific module.
    
    Args:
        name: Usually __name__ of the calling module
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name) 