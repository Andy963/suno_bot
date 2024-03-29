#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date     : 2024/3/29
# @FileName : logger.py # noqa
# Created by; Andy963

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class FileSplitLogger(metaclass=SingletonMeta):
    _loggers = {}

    def __init__(
        self,
        filename: str,
        level: int = logging.INFO,
        back_count: int = 5,
        max_bytes: int = 10 * 1024 * 1024,
        encoding: str = "utf-8",
        fmt: str = "%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s",
    ):
        identifier = (filename, level)
        if identifier not in self._loggers:
            self._loggers[identifier] = self._get_logger(
                filename, level, back_count, max_bytes, encoding, fmt
            )
        self.logger = self._loggers[identifier]

    def _get_logger(self, filename, level, back_count, max_bytes, encoding, fmt):
        logger = logging.getLogger(f"{filename}_{level}")
        logger.setLevel(level)

        log_dir = Path(filename).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        format_str = logging.Formatter(fmt)

        file_handler = RotatingFileHandler(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=back_count,
            encoding=encoding,
        )
        file_handler.setFormatter(format_str)
        logger.addHandler(file_handler)

        if os.getenv("DEBUG_MODE", "").lower() == "true":
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(format_str)
            logger.addHandler(console_handler)

        return logger

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)


if __name__ == "__main__":
    logger1 = FileSplitLogger("./logs/test.log", level=logging.DEBUG)
    logger2 = FileSplitLogger("./logs/test.log", level=logging.INFO)
    logger1.debug("This is a debug message")
    logger2.info("This is an info message")
