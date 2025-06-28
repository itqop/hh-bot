import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from .settings import AppConstants


class LoggingConfigurator:
    """Конфигуратор системы логирования"""

    @staticmethod
    def setup_logging(
        log_level: int = logging.INFO,
        log_file: Optional[str] = None,
        console_output: bool = False,
    ) -> None:
        """
        Настройка системы логирования

        Args:
            log_level: Уровень логирования
            log_file: Файл для записи логов (опционально)
            console_output: Выводить ли логи в консоль
        """

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        root_logger.handlers.clear()

        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=AppConstants.LOG_FILE_MAX_SIZE_MB * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

        logging.info("Логирование настроено")


def get_logger(name: str) -> logging.Logger:
    """Получение логгера для модуля"""
    return logging.getLogger(name)
