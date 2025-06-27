"""
🧪 Базовые тесты для HH.ru автоматизации
"""

import pytest
from hh_bot.config.settings import Settings
from hh_bot.models.vacancy import Vacancy, Employer, Experience, Snippet
from hh_bot.services.gemini_service import GeminiAIService
from hh_bot.services.hh_api_service import HHApiService


class TestModels:
    """Тесты моделей данных"""

    def test_vacancy_creation(self):
        """Тест создания вакансии"""
        employer = Employer(id="123", name="Test Company")
        experience = Experience(id="noExperience", name="Без опыта")
        snippet = Snippet(requirement="Python", responsibility="Программирование")

        vacancy = Vacancy(
            id="test_id",
            name="Python Developer",
            alternate_url="https://test.url",
            employer=employer,
            experience=experience,
            snippet=snippet,
        )

        assert vacancy.id == "test_id"
        assert vacancy.name == "Python Developer"
        assert vacancy.employer.name == "Test Company"

    def test_vacancy_has_python(self):
        """Тест проверки Python в вакансии"""
        employer = Employer(id="123", name="Test Company")
        experience = Experience(id="noExperience", name="Без опыта")
        snippet = Snippet(requirement="Python разработчик", responsibility="Кодинг")

        vacancy = Vacancy(
            id="test_id",
            name="Python Developer",
            alternate_url="https://test.url",
            employer=employer,
            experience=experience,
            snippet=snippet,
        )

        assert vacancy.has_python() is True

    def test_vacancy_is_junior_level(self):
        """Тест проверки junior уровня"""
        employer = Employer(id="123", name="Test Company")
        experience = Experience(id="noExperience", name="Без опыта")
        snippet = Snippet(requirement="Junior Python Developer")

        vacancy = Vacancy(
            id="test_id",
            name="Junior Python Developer",
            alternate_url="https://test.url",
            employer=employer,
            experience=experience,
            snippet=snippet,
        )

        assert vacancy.is_junior_level() is True


class TestSettings:
    """Тесты настроек"""

    def test_settings_creation(self):
        """Тест создания настроек"""
        settings = Settings()

        assert settings.hh_search.keywords == "python junior"
        assert settings.application.max_applications == 40
        assert settings.browser.headless is False

    def test_update_keywords(self):
        """Тест обновления ключевых слов"""
        settings = Settings()
        settings.update_search_keywords("django developer")

        assert settings.hh_search.keywords == "django developer"


class TestServices:
    """Тесты сервисов"""

    def test_gemini_service_creation(self):
        """Тест создания Gemini сервиса"""
        service = GeminiAIService()

        assert service.model == "gemini-2.0-flash"
        assert service.match_threshold == 0.7

    def test_hh_api_service_creation(self):
        """Тест создания HH API сервиса"""
        service = HHApiService()

        assert service.base_url == "https://api.hh.ru"
        assert service is not None

    def test_gemini_basic_analysis(self):
        """Тест базового анализа Gemini"""
        service = GeminiAIService()

        employer = Employer(id="123", name="Test Company")
        experience = Experience(id="noExperience", name="Без опыта")
        snippet = Snippet(requirement="Python", responsibility="Программирование")

        vacancy = Vacancy(
            id="test_id",
            name="Python Developer",
            alternate_url="https://test.url",
            employer=employer,
            experience=experience,
            snippet=snippet,
        )

        score, reasons = service._basic_analysis(vacancy)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert isinstance(reasons, list)
        assert len(reasons) > 0


def test_imports():
    """Тест что все импорты работают"""
    from hh_bot.config.settings import settings
    from hh_bot.services.gemini_service import GeminiAIService
    from hh_bot.services.hh_api_service import HHApiService
    from hh_bot.services.browser_service import BrowserService
    from hh_bot.core.job_application_manager import JobApplicationManager

    assert settings is not None
    assert GeminiAIService() is not None
    assert HHApiService() is not None
    assert BrowserService() is not None
    assert JobApplicationManager() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
