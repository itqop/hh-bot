"""
🔍 Сервис для работы с API HH.ru
"""

import requests
import time
from typing import List, Dict, Any, Optional
import traceback

from ..config.settings import settings, AppConstants
from ..models.vacancy import Vacancy, SearchStats


class VacancySearcher:
    """Отвечает только за поиск вакансий"""

    def __init__(self):
        self.base_url = AppConstants.HH_BASE_URL
        self.headers = {"User-Agent": "HH-Search-Bot/2.0 (job-search-automation)"}

    def search(self, keywords: Optional[str] = None) -> List[Vacancy]:
        """Поиск вакансий через API"""
        if keywords:
            settings.update_search_keywords(keywords)

        print(f"🔍 Поиск вакансий: {settings.hh_search.keywords}")
        all_vacancies = []

        try:
            for page in range(settings.hh_search.max_pages):
                print(f"📄 Обработка страницы {page + 1}...")

                page_vacancies = self._fetch_page(page)
                if not page_vacancies:
                    print(f"⚠️ Страница {page + 1} пуста, прекращаем поиск")
                    break

                all_vacancies.extend(page_vacancies)
                print(f"📋 Найдено {len(page_vacancies)} вакансий на странице {page + 1}")

                time.sleep(AppConstants.API_PAUSE_SECONDS)

            print(f"\n📊 Всего найдено: {len(all_vacancies)} вакансий")
            return all_vacancies

        except Exception as e:
            print(f"❌ Ошибка поиска вакансий: {e}")
            print(f"🔍 Traceback: {traceback.format_exc()}")
            return []

    def _fetch_page(self, page: int) -> List[Vacancy]:
        """Получение одной страницы результатов"""
        params = self._build_search_params(page)

        try:
            response = requests.get(
                f"{self.base_url}/vacancies",
                params=params,
                headers=self.headers,
                timeout=AppConstants.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            vacancies = []
            for item in items:
                try:
                    vacancy = Vacancy.from_api_response(item)
                    vacancies.append(vacancy)
                except Exception as e:
                    print(f"⚠️ Ошибка парсинга вакансии: {e}")
                    continue

            return vacancies

        except requests.RequestException as e:
            print(f"❌ Ошибка запроса к API HH.ru: {e}")
            return []
        except Exception as e:
            print(f"❌ Неожиданная ошибка при получении страницы: {e}")
            return []

    def _build_search_params(self, page: int) -> Dict[str, str]:
        """Построение параметров поиска"""
        config = settings.hh_search
        search_query = QueryBuilder.build_search_query(config.keywords)

        params = {
            "text": search_query,
            "area": config.area,
            "experience": config.experience,
            "per_page": str(config.per_page),
            "page": str(page),
            "order_by": config.order_by,
            "employment": "full,part",
            "schedule": "fullDay,remote,flexible",
            "only_with_salary": "false",
        }

        return params


class QueryBuilder:
    """Отвечает за построение поисковых запросов"""

    @staticmethod
    def build_search_query(keywords: str) -> str:
        """Построение умного поискового запроса"""
        base_queries = [
            keywords,
            f"{keywords} junior",
            f"{keywords} стажер",
            f"{keywords} начинающий",
            f"{keywords} без опыта",
        ]
        return " OR ".join(f"({query})" for query in base_queries)

    @staticmethod
    def suggest_keywords(base_keyword: str = "python") -> List[str]:
        """Предложения ключевых слов для поиска"""
        return [
            f"{base_keyword} junior",
            f"{base_keyword} стажер",
            f"{base_keyword} django",
            f"{base_keyword} flask",
            f"{base_keyword} fastapi",
            f"{base_keyword} web",
            f"{base_keyword} backend",
            f"{base_keyword} разработчик",
            f"{base_keyword} developer",
            f"{base_keyword} программист",
        ]


class VacancyFilter:
    """Отвечает за фильтрацию вакансий"""

    EXCLUDE_KEYWORDS = [
        "senior",
        "lead",
        "старший",
        "ведущий",
        "главный",
        "team lead",
        "tech lead",
        "архитектор",
        "head",
        "руководитель",
        "manager",
        "director",
    ]

    @staticmethod
    def filter_suitable(vacancies: List[Vacancy]) -> List[Vacancy]:
        """Фильтрация подходящих вакансий"""
        suitable = []

        for vacancy in vacancies:
            if VacancyFilter._is_suitable_basic(vacancy):
                suitable.append(vacancy)

        print(f"✅ После базовой фильтрации: {len(suitable)} подходящих вакансий")
        return suitable

    @staticmethod
    def _is_suitable_basic(vacancy: Vacancy) -> bool:
        """Базовая проверка подходящести вакансии"""

        if not vacancy.has_python():
            print(f"❌ Пропускаем '{vacancy.name}' - нет Python")
            return False

        text = vacancy.get_full_text().lower()
        for exclude in VacancyFilter.EXCLUDE_KEYWORDS:
            if exclude in text:
                print(f"❌ Пропускаем '{vacancy.name}' - содержит '{exclude}'")
                return False

        if vacancy.archived:
            print(f"❌ Пропускаем '{vacancy.name}' - архивная")
            return False

        print(f"✅ Подходящая вакансия: '{vacancy.name}'")
        return True


class VacancyDetailsFetcher:
    """Отвечает за получение детальной информации о вакансиях"""

    def __init__(self):
        self.base_url = AppConstants.HH_BASE_URL
        self.headers = {"User-Agent": "HH-Search-Bot/2.0 (job-search-automation)"}

    def get_details(self, vacancy_id: str) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о вакансии"""
        try:
            response = requests.get(
                f"{self.base_url}/vacancies/{vacancy_id}",
                headers=self.headers,
                timeout=AppConstants.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            print(f"❌ Ошибка получения деталей вакансии {vacancy_id}: {e}")
            return None


class HHApiService:
    """Главный сервис для работы с API HH.ru"""

    def __init__(self):
        self.searcher = VacancySearcher()
        self.filter = VacancyFilter()
        self.details_fetcher = VacancyDetailsFetcher()
        self.stats = SearchStats()

    def search_vacancies(self, keywords: Optional[str] = None) -> List[Vacancy]:
        """Поиск вакансий с фильтрацией"""
        vacancies = self.searcher.search(keywords)
        self.stats.total_found = len(vacancies)
        return vacancies

    def filter_suitable_vacancies(
        self, vacancies: List[Vacancy], use_basic_filter: bool = True
    ) -> List[Vacancy]:
        """Фильтрация подходящих вакансий"""
        if not use_basic_filter:
            return vacancies

        suitable = self.filter.filter_suitable(vacancies)
        self.stats.filtered_count = len(suitable)
        return suitable

    def get_vacancy_details(self, vacancy_id: str) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о вакансии"""
        return self.details_fetcher.get_details(vacancy_id)

    def get_search_stats(self) -> SearchStats:
        """Получение статистики поиска"""
        return self.stats

    def reset_stats(self) -> None:
        """Сброс статистики"""
        self.stats = SearchStats()

    def suggest_keywords(self, base_keyword: str = "python") -> List[str]:
        """Предложения ключевых слов для поиска"""
        return QueryBuilder.suggest_keywords(base_keyword)
