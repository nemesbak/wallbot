import locale
import logging
import sys
from logging.handlers import RotatingFileHandler

from src.wallbot.config.settings import LOG_LEVEL, LOG_PATH


def setup_logger():
    log_path = LOG_PATH
    level = getattr(logging, LOG_LEVEL)
    fmt = logging.Formatter('%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')

    handlers = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=10),
    ]
    for h in handlers:
        h.setFormatter(fmt)

    logging.basicConfig(level=level, handlers=handlers)
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
