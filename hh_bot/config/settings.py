import os
from dataclasses import dataclass
from pathlib import Path


class AppConstants:

    HH_BASE_URL = "https://api.hh.ru"
    HH_SITE_URL = "https://hh.ru"
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL = "gemini-2.0-flash"

    DEFAULT_TIMEOUT = 20
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

    keywords: str = "python"
    area: str = "1"
    experience: str = "noExperience"
    per_page: int = AppConstants.MAX_VACANCIES_PER_PAGE
    max_pages: int = 3
    order_by: str = "publication_time"


@dataclass
class BrowserConfig:

    headless: bool = False
    wait_timeout: int = 15
    page_load_timeout: int = 30
    implicit_wait: int = 10


@dataclass
class ApplicationConfig:

    max_applications: int = AppConstants.DEFAULT_MAX_APPLICATIONS
    pause_min: float = 3.0
    pause_max: float = 6.0
    manual_login: bool = True
    use_ai_cover_letters: bool = True


@dataclass
class GeminiConfig:

    api_key: str = ""
    model: str = AppConstants.GEMINI_MODEL
    base_url: str = AppConstants.GEMINI_BASE_URL
    match_threshold: float = AppConstants.DEFAULT_AI_THRESHOLD


@dataclass
class ResumeConfig:

    experience_file: str = AppConstants.DEFAULT_EXPERIENCE_FILE
    about_me_file: str = AppConstants.DEFAULT_ABOUT_FILE
    skills_file: str = AppConstants.DEFAULT_SKILLS_FILE


class ResumeFileManager:

    @staticmethod
    def create_sample_files() -> None:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        experience_file = data_dir / "experience.txt"
        if not experience_file.exists():
            experience_file.write_text(
                """
Опыт работы:
- ноль
""".strip(),
                encoding="utf-8",
            )
            print(f"✅ Создан файл: {experience_file}")

        about_file = data_dir / "about_me.txt"
        if not about_file.exists():
            about_file.write_text(
                """
О себе:
Котенок.
""".strip(),
                encoding="utf-8",
            )
            print(f"✅ Создан файл: {about_file}")

        skills_file = data_dir / "skills.txt"
        if not skills_file.exists():
            skills_file.write_text(
                """
Технические навыки:
- Мяу
""".strip(),
                encoding="utf-8",
            )
            print(f"✅ Создан файл: {skills_file}")


class UIFormatter:

    @staticmethod
    def create_separator(long: bool = False) -> str:
        length = (
            AppConstants.LONG_SEPARATOR_LENGTH
            if long
            else AppConstants.SHORT_SEPARATOR_LENGTH
        )
        return "=" * length

    @staticmethod
    def truncate_text(text: str, medium: bool = False) -> str:
        limit = (
            AppConstants.MEDIUM_TEXT_LIMIT if medium else AppConstants.SHORT_TEXT_LIMIT
        )
        return text[:limit]

    @staticmethod
    def format_percentage(value: float, total: float) -> str:
        if total <= 0:
            return "0.0%"
        percentage = (value / total) * AppConstants.PERCENT_MULTIPLIER
        return f"{percentage:.1f}%"

    @staticmethod
    def print_section_header(title: str, long: bool = False) -> None:
        separator = UIFormatter.create_separator(long)
        print(f"\n{separator}")
        print(title)
        print(separator)


class Settings:

    def __init__(self):
        self._load_env()

        self.hh_search = HHSearchConfig()
        self.browser = BrowserConfig()
        self.application = ApplicationConfig()
        self.gemini = GeminiConfig(api_key=os.getenv("GEMINI_API_KEY", ""))
        self.resume = ResumeConfig()

        self._validate_config()

    def _load_env(self) -> None:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            print("💡 Установите python-dotenv для работы с .env файлами")

    def _validate_config(self) -> None:
        if not self.gemini.api_key:
            print("⚠️ GEMINI_API_KEY не установлен в переменных окружения")

        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

    def update_search_keywords(self, keywords: str) -> None:
        self.hh_search.keywords = keywords
        print(f"🔄 Обновлены ключевые слова: {keywords}")

    def enable_ai_matching(self) -> bool:
        return bool(self.gemini.api_key)

    def get_exclude_keywords(self) -> list:
        return ["стажер", "cv"]


settings = Settings()
