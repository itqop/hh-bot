"""
🤖 Сервис для работы с Gemini AI
"""

import json
import requests
import logging
from typing import Dict, Optional, Tuple, List
import traceback
from pathlib import Path

from ..config.settings import settings, AppConstants
from ..models.vacancy import Vacancy

logger = logging.getLogger(__name__)


class GeminiApiClient:
    """Клиент для работы с Gemini API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = AppConstants.GEMINI_BASE_URL
        self.model = AppConstants.GEMINI_MODEL

    def generate_content(self, prompt: str) -> Optional[Dict]:
        """Генерация контента через Gemini API"""
        url = f"{self.base_url}/models/{self.model}:generateContent"

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": AppConstants.GEMINI_TEMPERATURE,
                "maxOutputTokens": AppConstants.GEMINI_MAX_OUTPUT_TOKENS,
            },
        }

        try:
            logger.info("Отправка запроса к Gemini API")
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=AppConstants.DEFAULT_TIMEOUT,
            )

            if response.status_code != 200:
                logger.error(f"Ошибка API Gemini: {response.status_code}, {response.text}")
                return None

            result = response.json()
            return self._parse_response(result)

        except requests.RequestException as e:
            logger.error(f"Ошибка сети при запросе к Gemini: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка Gemini API: {e}")
            return None

    def _parse_response(self, result: Dict) -> Optional[Dict]:
        """Парсинг ответа от Gemini API"""
        try:
            if "candidates" not in result or not result["candidates"]:
                logger.warning("Пустой ответ от Gemini")
                return None

            content = result["candidates"][0]["content"]["parts"][0]["text"]
            return self._extract_json_from_text(content)

        except (KeyError, IndexError) as e:
            logger.error(f"Ошибка структуры ответа Gemini: {e}")
            return None

    def _extract_json_from_text(self, content: str) -> Optional[Dict]:
        """Извлечение JSON из текстового ответа"""
        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed_response = json.loads(json_str)

                score = parsed_response.get("match_score", 0)
                logger.info(f"Gemini анализ завершен: {score}")
                return parsed_response
            else:
                logger.error("JSON не найден в ответе Gemini")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от Gemini: {e}")
            logger.debug(f"Контент: {content}")
            return None


class ResumeDataLoader:
    """Загрузчик данных резюме из файлов"""

    def __init__(self):
        self._cache: Optional[Dict[str, str]] = None

    def load(self) -> Dict[str, str]:
        """Загрузка данных резюме с кэшированием"""
        if self._cache is not None:
            return self._cache

        try:
            resume_data = self._load_from_files()
            self._cache = resume_data
            return resume_data
        except Exception as e:
            logger.error(f"Ошибка загрузки файлов резюме: {e}")
            return self._get_default_resume_data()

    def _load_from_files(self) -> Dict[str, str]:
        """Загрузка из файлов"""
        resume_data = {}

        file_mappings = {
            "experience": settings.resume.experience_file,
            "about_me": settings.resume.about_me_file,
            "skills": settings.resume.skills_file,
        }

        for key, relative_path in file_mappings.items():
            file_path = self._get_file_path(relative_path)

            if file_path.exists():
                resume_data[key] = file_path.read_text(encoding="utf-8")
                logger.info(f"Загружен {key} из {file_path}")
            else:
                resume_data[key] = self._get_default_value(key)
                logger.warning(f"Файл {file_path} не найден, используем заглушку")

        return resume_data

    def _get_file_path(self, relative_path: str) -> Path:
        """Получение абсолютного пути к файлу"""
        if Path(relative_path).is_absolute():
            return Path(relative_path)
        return Path.cwd() / relative_path

    def _get_default_value(self, key: str) -> str:
        """Получение значений по умолчанию"""
        defaults = {
            "experience": "Без опыта работы. Начинающий разработчик.",
            "about_me": "Начинающий Python разработчик, изучающий программирование.",
            "skills": "Python, SQL, Git, основы веб-разработки",
        }
        return defaults.get(key, "Не указано")

    def _get_default_resume_data(self) -> Dict[str, str]:
        """Полный набор данных по умолчанию"""
        return {
            "experience": self._get_default_value("experience"),
            "about_me": self._get_default_value("about_me"),
            "skills": self._get_default_value("skills"),
        }


class VacancyAnalyzer:
    """Анализатор соответствия вакансий"""

    def __init__(self, api_client: GeminiApiClient, resume_loader: ResumeDataLoader):
        self.api_client = api_client
        self.resume_loader = resume_loader
        self.match_threshold = settings.gemini.match_threshold

    def analyze(self, vacancy: Vacancy) -> Tuple[float, List[str]]:
        """Анализ соответствия вакансии резюме"""
        try:
            resume_data = self.resume_loader.load()
            prompt = self._create_prompt(vacancy, resume_data)

            response = self.api_client.generate_content(prompt)

            if response and "match_score" in response:
                score = float(response["match_score"])
                reasons = response.get("match_reasons", ["AI анализ выполнен"])
                return self._validate_score(score), reasons
            else:
                logger.warning("Ошибка анализа Gemini, используем базовую фильтрацию")
                return self._basic_analysis(vacancy)

        except Exception as e:
            logger.error(f"Ошибка в анализе Gemini: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return self._basic_analysis(vacancy)

    def _create_prompt(self, vacancy: Vacancy, resume_data: Dict[str, str]) -> str:
        """Создание промпта для анализа соответствия"""
        prompt = f"""
Проанализируй соответствие между резюме кандидата и вакансией.
Верни ТОЛЬКО JSON с такой структурой:
{{
    "match_score": 0.85,
    "match_reasons": ["причина1", "причина2"],
    "recommendation": "стоит откликаться"
}}

РЕЗЮМЕ КАНДИДАТА:
Опыт работы: {resume_data.get('experience', 'Не указан')}
О себе: {resume_data.get('about_me', 'Не указано')}
Навыки: {resume_data.get('skills', 'Не указаны')}

ВАКАНСИЯ:
Название: {vacancy.name}
Компания: {vacancy.employer.name}
Требования: {vacancy.snippet.requirement or 'Не указаны'}
Обязанности: {vacancy.snippet.responsibility or 'Не указаны'}
Опыт: {vacancy.experience.name}

Оцени соответствие от {AppConstants.MIN_AI_SCORE} до {AppConstants.MAX_AI_SCORE}, где:
- 0.0-0.3: Не подходит
- 0.4-0.6: Частично подходит
- 0.7-0.9: Хорошо подходит
- 0.9-1.0: Отлично подходит

В match_reasons укажи конкретные причины оценки.
В recommendation: "стоит откликаться", "стоит подумать" или "не стоит откликаться".
"""
        return prompt.strip()

    def _validate_score(self, score: float) -> float:
        """Валидация оценки AI"""
        return max(AppConstants.MIN_AI_SCORE, min(AppConstants.MAX_AI_SCORE, score))

    def _basic_analysis(self, vacancy: Vacancy) -> Tuple[float, List[str]]:
        """Базовый анализ без AI (фолбэк)"""
        score = 0.0
        reasons = []

        try:

            if vacancy.has_python():
                score += 0.4
                reasons.append("Содержит Python в требованиях")
            else:
                reasons.append("Не содержит Python в требованиях")
                return 0.1, reasons

            if vacancy.is_junior_level():
                score += 0.3
                reasons.append("Подходящий уровень (junior)")
            elif vacancy.experience.id in ["noExperience", "between1And3"]:
                score += 0.2
                reasons.append("Приемлемый опыт работы")

            if not vacancy.has_test:
                score += 0.1
                reasons.append("Без обязательного тестирования")
            else:
                reasons.append("Есть обязательное тестирование")

            if not vacancy.archived:
                score += 0.1
                reasons.append("Актуальная вакансия")

            return min(score, 1.0), reasons
        except Exception as e:
            logger.error(f"Ошибка базового анализа: {e}")
            return 0.0, ["Ошибка анализа"]

    def should_apply(self, vacancy: Vacancy) -> bool:
        """Принятие решения о подаче заявки"""
        try:
            score, reasons = self.analyze(vacancy)

            vacancy.ai_match_score = score
            vacancy.ai_match_reasons = reasons

            should_apply = score >= self.match_threshold

            if should_apply:
                logger.info(f"Рекомендуется откликаться (score: {score:.2f})")
            else:
                logger.info(f"Не рекомендуется откликаться (score: {score:.2f})")

            return should_apply
        except Exception as e:
            logger.error(f"Ошибка в should_apply: {e}")
            return False


class GeminiAIService:
    """Главный сервис для анализа вакансий с помощью Gemini AI"""

    def __init__(self):
        self.api_key = settings.gemini.api_key

        if self.api_key:
            self.api_client = GeminiApiClient(self.api_key)
        else:
            self.api_client = None

        self.resume_loader = ResumeDataLoader()

        if self.api_client:
            self.analyzer = VacancyAnalyzer(self.api_client, self.resume_loader)
        else:
            self.analyzer = None

    def is_available(self) -> bool:
        """Проверка доступности сервиса"""
        return bool(self.api_key)

    def load_resume_data(self) -> Dict[str, str]:
        """Загрузка данных резюме из файлов"""
        return self.resume_loader.load()

    def analyze_vacancy_match(self, vacancy: Vacancy) -> Tuple[float, List[str]]:
        """Анализ соответствия вакансии резюме"""
        if not self.is_available() or not self.analyzer:
            logger.warning("Gemini API недоступен, используем базовую фильтрацию")
            return VacancyAnalyzer(None, self.resume_loader)._basic_analysis(vacancy)

        return self.analyzer.analyze(vacancy)

    def should_apply(self, vacancy: Vacancy) -> bool:
        """Принятие решения о подаче заявки"""
        if not self.is_available() or not self.analyzer:

            score, _ = VacancyAnalyzer(None, self.resume_loader)._basic_analysis(vacancy)
            return score >= settings.gemini.match_threshold

        return self.analyzer.should_apply(vacancy)
