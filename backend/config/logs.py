import logging
from logging.handlers import RotatingFileHandler
import os

from config.settings import get_settings

class LoggerManager:
    _logger = None # class variable to store the logger instance

    def __init__(self, log_file_path="logs/app.log"):
        # initialize the logger with the provided log file path
        self.settings = get_settings()
        self.log_file_path = log_file_path
        self.max_bytes = self.settings.BACK_LOG_MAX_BYTES
        self.backup_count = self.settings.BACK_LOG_BACKUP_COUNT

        # create the log directory if it does not exist
        log_dir = os.path.dirname(self.log_file_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # setup the logger
        self._setup_logger()

    def _setup_logger(self):
        # setup logger if it hasn't been initialized yet
        if LoggerManager._logger is None:
            # create a rotating file handler
            handler = RotatingFileHandler(self.log_file_path, maxBytes=self.max_bytes, backupCount=self.backup_count)
            
            # define log levels
            log_levels = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
            
            # set log level based on settings
            handler.setLevel(log_levels.get(self.settings.BACK_LOGGING_LEVEL, logging.INFO))
            
            # set log format
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S %z")
            handler.setFormatter(formatter)

            # create logger instance
            logger = logging.getLogger("app_logger")
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

            # store the logger instance in the class variable
            LoggerManager._logger = logger

    def _get_logger(self):
        # retrieve the logger instance, setup if it hasn't been initialized yet
        if LoggerManager._logger is None:
            self._setup_logger()
        return LoggerManager._logger

    def debug(self, message):
        print("DEBUG", message)
        logger = self._get_logger()
        logger.debug(message)
        
    def info(self, message):
        print("INFO", message)
        logger = self._get_logger()
        logger.info(message)

    def warning(self, message):
        print("WARNING", message)
        logger = self._get_logger()
        logger.warning(message)

    def error(self, message):
        print("ERROR", message)
        logger = self._get_logger()
        logger.error(message)
        
    def critical(self, message):
        print("CRITICAL", message)
        logger = self._get_logger()
        logger.critical(message)
