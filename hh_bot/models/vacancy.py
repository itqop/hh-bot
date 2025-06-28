from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import re


@dataclass
class Employer:

    id: str
    name: str
    url: Optional[str] = None
    alternate_url: Optional[str] = None
    logo_urls: Optional[Dict[str, str]] = None
    vacancies_url: Optional[str] = None
    trusted: bool = False


@dataclass
class Experience:

    id: str
    name: str


@dataclass
class Snippet:

    requirement: Optional[str] = None
    responsibility: Optional[str] = None


@dataclass
class Salary:

    from_value: Optional[int] = None
    to_value: Optional[int] = None
    currency: str = "RUR"
    gross: bool = False


@dataclass
class Vacancy:

    id: str
    name: str
    alternate_url: str
    employer: Employer
    experience: Experience
    snippet: Snippet
    premium: bool = False
    has_test: bool = False
    response_letter_required: bool = False
    archived: bool = False
    apply_alternate_url: Optional[str] = None

    ai_match_score: Optional[float] = None
    ai_match_reasons: List[str] = field(default_factory=list)

    salary: Optional[Salary] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Vacancy":
        try:

            employer_data = data.get("employer", {})
            employer = Employer(
                id=employer_data.get("id", ""),
                name=employer_data.get("name", "Неизвестная компания"),
                url=employer_data.get("url"),
                alternate_url=employer_data.get("alternate_url"),
                logo_urls=employer_data.get("logo_urls"),
                vacancies_url=employer_data.get("vacancies_url"),
                trusted=employer_data.get("trusted", False),
            )

            experience_data = data.get("experience", {})
            experience = Experience(
                id=experience_data.get("id", "noExperience"),
                name=experience_data.get("name", "Без опыта"),
            )

            snippet_data = data.get("snippet", {})
            snippet = Snippet(
                requirement=snippet_data.get("requirement"),
                responsibility=snippet_data.get("responsibility"),
            )

            salary = None
            salary_data = data.get("salary")
            if salary_data:
                salary = Salary(
                    from_value=salary_data.get("from"),
                    to_value=salary_data.get("to"),
                    currency=salary_data.get("currency", "RUR"),
                    gross=salary_data.get("gross", False),
                )

            return cls(
                id=data.get("id", ""),
                name=data.get("name", "Без названия"),
                alternate_url=data.get("alternate_url", ""),
                employer=employer,
                experience=experience,
                snippet=snippet,
                premium=data.get("premium", False),
                has_test=data.get("has_test", False),
                response_letter_required=data.get("response_letter_required", False),
                archived=data.get("archived", False),
                apply_alternate_url=data.get("apply_alternate_url"),
                salary=salary,
            )
        except Exception as e:
            print(f"❌ Ошибка парсинга вакансии: {e}")

            return cls(
                id=data.get("id", "unknown"),
                name=data.get("name", "Ошибка загрузки"),
                alternate_url=data.get("alternate_url", ""),
                employer=Employer(id="", name="Неизвестно"),
                experience=Experience(id="noExperience", name="Без опыта"),
                snippet=Snippet(),
            )

    def has_python(self) -> bool:
        text_to_check = (
            f"{self.name} {self.snippet.requirement or ''} "
            f"{self.snippet.responsibility or ''}"
        )
        python_patterns = [
            r"\bpython\b",
            r"\bпайтон\b",
            r"\bджанго\b",
            r"\bflask\b",
            r"\bfastapi\b",
            r"\bpandas\b",
            r"\bnumpy\b",
        ]

        for pattern in python_patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True
        return False

    def matches_keywords(self, keywords: str) -> bool:
        text_to_check = (
            f"{self.name} {self.snippet.requirement or ''} "
            f"{self.snippet.responsibility or ''}"
        ).lower()

        search_terms = [term.strip().lower() for term in keywords.split()]

        for term in search_terms:
            if term in text_to_check:
                return True
        return False

    def is_junior_level(self) -> bool:
        junior_keywords = [
            "junior",
            "джуниор",
            "стажер",
            "стажёр",
            "начинающий",
            "intern",
            "trainee",
            "entry",
            "младший",
        ]

        text_to_check = f"{self.name} {self.snippet.requirement or ''}"

        for keyword in junior_keywords:
            if keyword.lower() in text_to_check.lower():
                return True
        return False

    def get_salary_info(self) -> str:
        if not self.salary:
            return "Зарплата не указана"

        from_val = self.salary.from_value
        to_val = self.salary.to_value
        currency = self.salary.currency
        gross_suffix = " (до вычета налогов)" if self.salary.gross else " (на руки)"

        if from_val and to_val:
            return f"{from_val:,} - {to_val:,} {currency}{gross_suffix}"
        elif from_val:
            return f"от {from_val:,} {currency}{gross_suffix}"
        elif to_val:
            return f"до {to_val:,} {currency}{gross_suffix}"
        else:
            return "Зарплата не указана"

    def get_full_text(self) -> str:
        text_parts = [
            self.name,
            self.employer.name,
            self.snippet.requirement or "",
            self.snippet.responsibility or "",
            self.experience.name,
        ]
        return " ".join(filter(None, text_parts))


@dataclass
class ApplicationResult:

    vacancy_id: str
    vacancy_name: str
    success: bool
    already_applied: bool = False
    skipped: bool = False
    error_message: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            from datetime import datetime

            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class SearchStats:

    total_found: int = 0
    pages_processed: int = 0
    filtered_count: int = 0
    python_vacancies: int = 0
    junior_vacancies: int = 0
    with_salary: int = 0
    without_test: int = 0

    def __str__(self) -> str:
        return (
            f"📊 Статистика поиска:\n"
            f"   📋 Всего найдено: {self.total_found}\n"
            f"   📄 Страниц обработано: {self.pages_processed}\n"
            f"   ✅ Прошло фильтрацию: {self.filtered_count}\n"
            f"   🐍 Python вакансий: {self.python_vacancies}\n"
            f"   👶 Junior уровня: {self.junior_vacancies}\n"
            f"   💰 С указанной ЗП: {self.with_salary}\n"
            f"   📝 Без тестов: {self.without_test}"
        )
