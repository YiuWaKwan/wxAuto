#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''
  log out level
  logging.DEBUG:   10
  logging.INFO:    20
  logging.WARN:    30
  logging.ERROR:   40
  logging.CRITICAL:50
'''
import logging
import logging.handlers
import logging.config

class FinalLogger:
    log = None
    log_max_byte = 700 * 1024 * 1024
    log_backup_count = 5

    def __init__(self, log_max_byte=700 * 1024 * 1024, log_backup_count=5):
        self.log_max_byte = log_max_byte
        self.log_backup_count = log_backup_count

    def getConfLogger(self,log_file):
        LOGGING_MSG_FORMAT = logging.Formatter("%(asctime)s %(levelname)s %(filename)s %(funcName)s (line:%(lineno)d)[%(process)d][%(threadName)s][%(message)s]")
        log = logging.Logger("")
        log_handler = logging.handlers.RotatingFileHandler(filename=log_file,
                                                           maxBytes=self.log_max_byte,
                                                           backupCount=self.log_backup_count)
        log_handler.setLevel(logging.DEBUG)
        log_handler.suffix = "%Y%m%d-%H%M"
        log_handler.setFormatter(LOGGING_MSG_FORMAT)
        log.addHandler(log_handler)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(LOGGING_MSG_FORMAT)
        log.addHandler(console)
        return log

    @staticmethod
    def get_logger(log_file, log_level=20, console=False):
        if FinalLogger.log is not None:
            return FinalLogger.log

        FinalLogger.logger = logging.Logger("")

        log_handler = logging.handlers.TimedRotatingFileHandler(log_file, when="d", interval=1, backupCount=1000)

        log_fmt = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
        log_handler.setFormatter(log_fmt)
        FinalLogger.logger.addHandler(log_handler)
        FinalLogger.logger.setLevel(log_level)

        if console:
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            console.setFormatter(log_fmt)
            FinalLogger.logger.addHandler(console)
        return FinalLogger.logger