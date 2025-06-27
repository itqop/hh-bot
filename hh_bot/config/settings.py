"""
⚙️ Конфигурация для HH.ru автоматизации
"""

import os
from dataclasses import dataclass
from pathlib import Path


class AppConstants:
    """Константы приложения"""

    HH_BASE_URL = "https://api.hh.ru"
    HH_SITE_URL = "https://hh.ru"
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL = "gemini-2.0-flash"

    DEFAULT_TIMEOUT = 30
    API_PAUSE_SECONDS = 0.5
    AI_REQUEST_PAUSE = 1

    MAX_VACANCIES_PER_PAGE = 50
    MAX_SEARCH_PAGES = 5
    DEFAULT_MAX_APPLICATIONS = 40

    DEFAULT_EXPERIENCE_FILE = "data/experience.txt"
    DEFAULT_ABOUT_FILE = "data/about_me.txt"
    DEFAULT_SKILLS_FILE = "data/skills.txt"

    DEFAULT_AI_THRESHOLD = 0.7
    MIN_AI_SCORE = 0.0
    MAX_AI_SCORE = 1.0

    SHORT_SEPARATOR_LENGTH = 50
    LONG_SEPARATOR_LENGTH = 60
    SHORT_TEXT_LIMIT = 50
    MEDIUM_TEXT_LIMIT = 60

    GEMINI_TEMPERATURE = 0.3
    GEMINI_MAX_OUTPUT_TOKENS = 1000

    LOG_FILE_MAX_SIZE_MB = 10
    PERCENT_MULTIPLIER = 100


@dataclass
class HHSearchConfig:
    """Настройки поиска вакансий"""

    keywords: str = "python junior"
    area: str = "1"
    experience: str = "noExperience"
    per_page: int = AppConstants.MAX_VACANCIES_PER_PAGE
    max_pages: int = 3
    order_by: str = "publication_time"


@dataclass
class BrowserConfig:
    """Настройки браузера"""

    headless: bool = False
    wait_timeout: int = 15
    page_load_timeout: int = 30
    implicit_wait: int = 10


@dataclass
class ApplicationConfig:
    """Настройки подачи заявок"""

    max_applications: int = AppConstants.DEFAULT_MAX_APPLICATIONS
    pause_min: float = 3.0
    pause_max: float = 6.0
    manual_login: bool = True


@dataclass
class GeminiConfig:
    """Настройки Gemini AI"""

    api_key: str = ""
    model: str = AppConstants.GEMINI_MODEL
    base_url: str = AppConstants.GEMINI_BASE_URL
    match_threshold: float = AppConstants.DEFAULT_AI_THRESHOLD


@dataclass
class ResumeConfig:
    """Настройки резюме"""

    experience_file: str = AppConstants.DEFAULT_EXPERIENCE_FILE
    about_me_file: str = AppConstants.DEFAULT_ABOUT_FILE
    skills_file: str = AppConstants.DEFAULT_SKILLS_FILE


class ResumeFileManager:
    """Менеджер для работы с файлами резюме"""

    @staticmethod
    def create_sample_files() -> None:
        """Создание примеров файлов резюме"""
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        experience_file = data_dir / "experience.txt"
        if not experience_file.exists():
            experience_file.write_text(
                """
Опыт работы:
- Изучаю Python уже 6 месяцев
- Прошел курсы по основам программирования
- Делал учебные проекты: калькулятор, игра в крестики-нолики
- Изучаю Django и Flask для веб-разработки
- Базовые знания SQL и работы с базами данных
- Знаком с Git для контроля версий
""".strip(),
                encoding="utf-8",
            )
            print(f"✅ Создан файл: {experience_file}")

        about_file = data_dir / "about_me.txt"
        if not about_file.exists():
            about_file.write_text(
                """
О себе:
Начинающий Python разработчик с большим желанием учиться и развиваться.
Интересуюсь веб-разработкой и анализом данных.
Быстро обучаюсь, ответственно подхожу к работе.
Готов к стажировке или junior позиции для получения практического опыта.
Хочу работать в команде опытных разработчиков и вносить вклад в интересные проекты.
""".strip(),
                encoding="utf-8",
            )
            print(f"✅ Создан файл: {about_file}")

        skills_file = data_dir / "skills.txt"
        if not skills_file.exists():
            skills_file.write_text(
                """
Технические навыки:
- Python (основы, ООП, модули)
- SQL (SELECT, JOIN, базовые запросы)
- Git (commit, push, pull, merge)
- HTML/CSS (базовые знания)
- Django (учебные проекты)
- Flask (микрофреймворк)
- PostgreSQL, SQLite
- Linux (базовые команды)
- VS Code, PyCharm
""".strip(),
                encoding="utf-8",
            )
            print(f"✅ Создан файл: {skills_file}")


class UIFormatter:
    """Утилиты для форматирования пользовательского интерфейса"""

    @staticmethod
    def create_separator(long: bool = False) -> str:
        """Создание разделительной линии"""
        length = AppConstants.LONG_SEPARATOR_LENGTH if long else AppConstants.SHORT_SEPARATOR_LENGTH
        return "=" * length

    @staticmethod
    def truncate_text(text: str, medium: bool = False) -> str:
        """Обрезание текста до заданного лимита"""
        limit = AppConstants.MEDIUM_TEXT_LIMIT if medium else AppConstants.SHORT_TEXT_LIMIT
        return text[:limit]

    @staticmethod
    def format_percentage(value: float, total: float) -> str:
        """Форматирование процентного соотношения"""
        if total <= 0:
            return "0.0%"
        percentage = (value / total) * AppConstants.PERCENT_MULTIPLIER
        return f"{percentage:.1f}%"

    @staticmethod
    def print_section_header(title: str, long: bool = False) -> None:
        """Печать заголовка секции с разделителями"""
        separator = UIFormatter.create_separator(long)
        print(f"\n{separator}")
        print(title)
        print(separator)


class Settings:
    """Главный класс настроек"""

    def __init__(self):

        self._load_env()

        self.hh_search = HHSearchConfig()
        self.browser = BrowserConfig()
        self.application = ApplicationConfig()
        self.gemini = GeminiConfig(api_key=os.getenv("GEMINI_API_KEY", ""))
        self.resume = ResumeConfig()

        self._validate_config()

    def _load_env(self) -> None:
        """Загрузка переменных окружения"""
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            print("💡 Установите python-dotenv для работы с .env файлами")

    def _validate_config(self) -> None:
        """Валидация настроек"""
        if not self.gemini.api_key:
            print("⚠️ GEMINI_API_KEY не установлен в переменных окружения")

        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

    def update_search_keywords(self, keywords: str) -> None:
        """Обновление ключевых слов поиска"""
        self.hh_search.keywords = keywords
        print(f"🔄 Обновлены ключевые слова: {keywords}")

    def enable_ai_matching(self) -> bool:
        """Проверяем можно ли использовать AI сравнение"""
        return bool(self.gemini.api_key)


settings = Settings()
