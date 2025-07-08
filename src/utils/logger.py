import logging
import sys


def setup_logger(name: str = "agentic", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # avoid duplicate handlers

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s: %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(level)
    return logger 