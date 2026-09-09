import logging


class Logger:
    def __init__(self, name="Nexora"):
        self._logger = logging.getLogger(name)

        if not self._logger.handlers:
            handler = logging.StreamHandler()

            formatter = logging.Formatter(
                "[%(levelname)s] %(message)s"
            )

            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

        self._logger.setLevel(logging.INFO)

    def debug(self, message):
        self._logger.debug(message)

    def info(self, message):
        self._logger.info(message)

    def warning(self, message):
        self._logger.warning(message)

    def error(self, message):
        self._logger.error(message)

    def critical(self, message):
        self._logger.critical(message)