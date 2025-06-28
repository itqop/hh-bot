import requests
import time
from typing import List, Dict, Any, Optional
import traceback

from ..config.settings import settings, AppConstants
from ..models.vacancy import Vacancy, SearchStats


class VacancySearcher:

    def __init__(self):
        self.base_url = AppConstants.HH_BASE_URL
        self.headers = {"User-Agent": "HH-Search-Bot/2.0 (job-search-automation)"}

    def search(self, keywords: Optional[str] = None) -> List[Vacancy]:
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
                print(
                    f"📋 Найдено {len(page_vacancies)} вакансий на странице {page + 1}"
                )

                time.sleep(AppConstants.API_PAUSE_SECONDS)

            print(f"\n📊 Всего найдено: {len(all_vacancies)} вакансий")
            return all_vacancies

        except Exception as e:
            print(f"❌ Ошибка поиска вакансий: {e}")
            print(f"🔍 Traceback: {traceback.format_exc()}")
            return []

    def _fetch_page(self, page: int) -> List[Vacancy]:
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
        config = settings.hh_search
        search_query = QueryBuilder.build_search_query(config.keywords)

        params = {
            "text": search_query,
            "area": config.area,
            "per_page": str(min(config.per_page, 20)),
            "page": str(page),
            "order_by": "publication_time",
        }

        return params


class QueryBuilder:

    @staticmethod
    def build_search_query(keywords: str) -> str:
        return keywords


class VacancyFilter:

    @staticmethod
    def filter_suitable(
        vacancies: List[Vacancy], search_keywords: str = ""
    ) -> List[Vacancy]:
        suitable = []

        for vacancy in vacancies:
            if VacancyFilter._is_suitable_basic(vacancy, search_keywords):
                suitable.append(vacancy)

        print(f"✅ После базовой фильтрации: {len(suitable)} подходящих вакансий")
        return suitable

    @staticmethod
    def _is_suitable_basic(vacancy: Vacancy, search_keywords: str = "") -> bool:
        if search_keywords and not vacancy.matches_keywords(search_keywords):
            print(f"❌ Пропускаем '{vacancy.name}' - не соответствует ключевым словам")
            return False

        if not search_keywords and not vacancy.has_python():
            print(f"❌ Пропускаем '{vacancy.name}' - нет Python")
            return False

        text = vacancy.get_full_text().lower()
        for exclude in settings.get_exclude_keywords():
            if exclude in text:
                print(f"❌ Пропускаем '{vacancy.name}' - содержит '{exclude}'")
                return False

        if vacancy.archived:
            print(f"❌ Пропускаем '{vacancy.name}' - архивная")
            return False

        print(f"✅ Подходящая вакансия: '{vacancy.name}'")
        return True


class VacancyDetailsFetcher:

    def __init__(self):
        self.base_url = AppConstants.HH_BASE_URL
        self.headers = {"User-Agent": "HH-Search-Bot/2.0 (job-search-automation)"}

    def get_details(self, vacancy_id: str) -> Optional[Dict[str, Any]]:
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

    def __init__(self):
        self.searcher = VacancySearcher()
        self.filter = VacancyFilter()
        self.details_fetcher = VacancyDetailsFetcher()
        self.stats = SearchStats()

    def search_vacancies(self, keywords: Optional[str] = None) -> List[Vacancy]:
        vacancies = self.searcher.search(keywords)
        self.stats.total_found = len(vacancies)
        return vacancies

    def filter_suitable_vacancies(
        self,
        vacancies: List[Vacancy],
        use_basic_filter: bool = True,
        search_keywords: str = "",
    ) -> List[Vacancy]:
        if not use_basic_filter:
            return vacancies

        suitable = self.filter.filter_suitable(vacancies, search_keywords)
        self.stats.filtered_count = len(suitable)
        return suitable

    def get_vacancy_details(self, vacancy_id: str) -> Optional[Dict[str, Any]]:
        return self.details_fetcher.get_details(vacancy_id)

    def get_search_stats(self) -> SearchStats:
        return self.stats

    def reset_stats(self) -> None:
        self.stats = SearchStats()
