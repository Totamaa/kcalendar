import logging
from logging.handlers import RotatingFileHandler
import os

from config.settings import get_settings

class LoggerManager:
    def __init__(self, log_file_path="logs/app.log"):
        settings = get_settings()
        self.log_file_path = log_file_path
        self.max_bytes = settings.BACK_LOG_MAX_BYTES
        self.backup_count = settings.BACK_LOG_BACKUP_COUNT
        
        log_dir = os.path.dirname(self.log_file_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def _create_handler(self):
        handler = RotatingFileHandler(self.log_file_path, maxBytes=self.max_bytes, backupCount=self.backup_count)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S %z")
        handler.setFormatter(formatter)
        return handler

    def _get_logger(self):
        logger = logging.getLogger("app_logger")
        logger.setLevel(logging.INFO)
        handler = self._create_handler()
        logger.addHandler(handler)
        return logger, handler

    def info(self, message):
        logger, handler = self._get_logger()
        print(message)
        logger.info(message)
        self._close_handler(logger, handler)

    def warning(self, message):
        logger, handler = self._get_logger()
        print(message)
        logger.warning(message)
        self._close_handler(logger, handler)

    def error(self, message):
        logger, handler = self._get_logger()
        print(message)
        logger.error(message)
        self._close_handler(logger, handler)
        
    def debug(self, message):
        logger, handler = self._get_logger()
        print(message)
        logger.debug(message)
        self._close_handler(logger, handler)

    def _close_handler(self, logger, handler):
        handler.close()
        logger.removeHandler(handler)