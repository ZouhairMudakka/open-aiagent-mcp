import logging
import sys


def setup_logger(name: str = "agentic", level: str = "INFO") -> logging.Logger:
    # Reuse Uvicorn's error logger handlers so our output always appears in console
    base_logger = logging.getLogger("uvicorn.error")
    logger = logging.getLogger(name)
    if base_logger.handlers and not logger.handlers:
        for h in base_logger.handlers:
            logger.addHandler(h)
    logger.propagate = False
    if logger.handlers:
        return logger  # avoid duplicate handlers

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s: %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(level)
    return logger 