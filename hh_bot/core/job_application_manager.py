"""
🎯 Главный менеджер для автоматизации откликов на вакансии
"""

import logging
from typing import List, Dict, Optional
import time

from ..config.settings import settings, AppConstants, UIFormatter
from ..config.logging_config import LoggingConfigurator
from ..models.vacancy import Vacancy, ApplicationResult
from ..services.hh_api_service import HHApiService
from ..services.gemini_service import GeminiAIService
from ..services.browser_service import BrowserService

logger = logging.getLogger(__name__)


class AutomationOrchestrator:
    """Оркестратор процесса автоматизации"""

    def __init__(self):
        self.api_service = HHApiService()
        self.ai_service = GeminiAIService()
        self.browser_service = BrowserService()

    def execute_automation_pipeline(
        self, keywords: Optional[str] = None, use_ai: bool = True
    ) -> Dict:
        """Выполнение полного пайплайна автоматизации"""
        try:

            vacancies = self._search_and_filter_vacancies(keywords)
            if not vacancies:
                return {"error": "Подходящие вакансии не найдены"}

            if use_ai and self.ai_service.is_available():
                vacancies = self._ai_filter_vacancies(vacancies)
                if not vacancies:
                    return {"error": "После AI фильтрации не осталось подходящих вакансий"}

            if not self._initialize_browser_and_auth():
                return {"error": "Ошибка инициализации браузера или авторизации"}

            application_results = self._apply_to_vacancies(vacancies)

            return self._create_stats(application_results)

        except KeyboardInterrupt:
            logger.info("Процесс остановлен пользователем")
            return {"error": "Остановлено пользователем"}
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            return {"error": str(e)}
        finally:
            self._cleanup()

    def _search_and_filter_vacancies(self, keywords: Optional[str] = None) -> List[Vacancy]:
        """Поиск и базовая фильтрация вакансий"""
        logger.info("🔍 ЭТАП 1: Поиск вакансий")

        try:
            all_vacancies = self.api_service.search_vacancies(keywords)
            if not all_vacancies:
                logger.warning("Вакансии не найдены через API")
                return []

            suitable_vacancies = self.api_service.filter_suitable_vacancies(all_vacancies)

            self._log_search_results(all_vacancies, suitable_vacancies)
            return suitable_vacancies

        except Exception as e:
            logger.error(f"Ошибка поиска вакансий: {e}")
            return []

    def _ai_filter_vacancies(self, vacancies: List[Vacancy]) -> List[Vacancy]:
        """AI фильтрация вакансий"""
        logger.info("🤖 ЭТАП 2: AI анализ вакансий")

        ai_suitable = []
        total_count = len(vacancies)

        for i, vacancy in enumerate(vacancies, 1):
            truncated_name = UIFormatter.truncate_text(vacancy.name)
            logger.info(f"Анализ {i}/{total_count}: {truncated_name}...")

            try:
                if self.ai_service.should_apply(vacancy):
                    ai_suitable.append(vacancy)
                    logger.info("✅ Добавлено в список для отклика")
                else:
                    logger.info("❌ Не рекомендуется")

                if i < total_count:
                    time.sleep(AppConstants.AI_REQUEST_PAUSE)

            except Exception as e:
                logger.error(f"Ошибка AI анализа: {e}")
                ai_suitable.append(vacancy)

        self._log_ai_results(total_count, ai_suitable)
        return ai_suitable

    def _initialize_browser_and_auth(self) -> bool:
        """Инициализация браузера и авторизация"""
        logger.info("🌐 ЭТАП 3: Инициализация браузера и авторизация")

        try:
            if not self.browser_service.initialize():
                logger.error("Не удалось инициализировать браузер")
                return False

            if not self.browser_service.authenticate_interactive():
                logger.error("Не удалось авторизоваться")
                return False

            logger.info("✅ Браузер готов к работе")
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            return False

    def _apply_to_vacancies(self, vacancies: List[Vacancy]) -> List[ApplicationResult]:
        """Подача заявок на вакансии"""
        max_apps = settings.application.max_applications
        vacancies_to_process = vacancies[:max_apps]

        logger.info(f"📨 ЭТАП 4: Подача заявок (максимум {max_apps})")
        logger.info("💡 Между заявками добавляются паузы для безопасности")

        application_results = []

        for i, vacancy in enumerate(vacancies_to_process, 1):
            truncated_name = UIFormatter.truncate_text(vacancy.name, medium=True)
            logger.info(f"Обработка {i}/{len(vacancies_to_process)}: {truncated_name}...")

            try:
                result = self.browser_service.apply_to_vacancy(vacancy.alternate_url, vacancy.name)
                application_results.append(result)
                self._log_application_result(result)

                if i < len(vacancies_to_process):
                    self.browser_service.add_random_pause()

            except Exception as e:
                logger.error(f"Неожиданная ошибка при подаче заявки: {e}")
                error_result = ApplicationResult(
                    vacancy_id="",
                    vacancy_name=vacancy.name,
                    success=False,
                    error_message=str(e),
                )
                application_results.append(error_result)

        return application_results

    def _log_search_results(self, all_vacancies: List[Vacancy], suitable: List[Vacancy]):
        """Логирование результатов поиска"""
        logger.info("📊 Результат базовой фильтрации:")
        logger.info(f"   🔍 Всего: {len(all_vacancies)}")
        logger.info(f"   ✅ Подходящих: {len(suitable)}")
        if len(all_vacancies) > 0:
            percentage = UIFormatter.format_percentage(len(suitable), len(all_vacancies))
            logger.info(f"   📈 % соответствия: {percentage}")

    def _log_ai_results(self, total_analyzed: int, ai_suitable: List[Vacancy]):
        """Логирование результатов AI анализа"""
        logger.info("🎯 AI фильтрация завершена:")
        logger.info(f"   🤖 Проанализировано: {total_analyzed}")
        logger.info(f"   ✅ Рекомендовано: {len(ai_suitable)}")
        if total_analyzed > 0:
            percentage = UIFormatter.format_percentage(len(ai_suitable), total_analyzed)
            logger.info(f"   📈 % одобрения: {percentage}")

    def _log_application_result(self, result: ApplicationResult):
        """Логирование результата подачи заявки"""
        if result.success:
            logger.info("   ✅ Заявка отправлена успешно")
        elif result.already_applied:
            logger.info("   ⚠️ Уже откликались ранее")
        else:
            logger.warning(f"   ❌ Ошибка: {result.error_message}")

    def _create_stats(self, application_results: List[ApplicationResult]) -> Dict:
        """Создание итоговой статистики"""
        total_applications = len(application_results)
        successful = sum(1 for r in application_results if r.success)
        already_applied = sum(1 for r in application_results if r.already_applied)
        failed = total_applications - successful - already_applied

        return {
            "total_applications": total_applications,
            "successful": successful,
            "failed": failed,
            "already_applied": already_applied,
        }

    def _cleanup(self):
        """Очистка ресурсов"""
        logger.info("🔒 Закрытие браузера...")
        self.browser_service.close()


class JobApplicationManager:
    """Главный менеджер для управления процессом поиска и откликов на вакансии"""

    def __init__(self):

        LoggingConfigurator.setup_logging(log_file="logs/hh_bot.log", console_output=False)

        self.orchestrator = AutomationOrchestrator()
        self.application_results: List[ApplicationResult] = []

    def run_automation(self, keywords: Optional[str] = None, use_ai: bool = True) -> Dict:
        """Запуск полного цикла автоматизации"""
        print("🚀 Запуск автоматизации HH.ru")
        print(UIFormatter.create_separator())

        stats = self.orchestrator.execute_automation_pipeline(keywords, use_ai)

        if "error" not in stats:

            pass

        return stats

    def get_application_results(self) -> List[ApplicationResult]:
        """Получение результатов подачи заявок"""
        return self.application_results.copy()

    def print_detailed_report(self, stats: Dict) -> None:
        """Детальный отчет о работе"""
        UIFormatter.print_section_header("📊 ДЕТАЛЬНЫЙ ОТЧЕТ", long=True)

        if "error" in stats:
            print(f"❌ Ошибка выполнения: {stats['error']}")
            return

        print(f"📝 Всего попыток подачи заявок: {stats['total_applications']}")
        print(f"✅ Успешно отправлено: {stats['successful']}")
        print(f"⚠️ Уже откликались ранее: {stats['already_applied']}")
        print(f"❌ Неудачных попыток: {stats['failed']}")

        if stats["total_applications"] > 0:
            success_rate = UIFormatter.format_percentage(
                stats["successful"], stats["total_applications"]
            )
            print(f"📈 Успешность: {success_rate}")

        print(UIFormatter.create_separator(long=True))

        if stats["successful"] > 0:
            print(f"🎉 Отлично! Отправлено {stats['successful']} новых заявок!")
            print("💡 Рекомендуется запускать автоматизацию 2-3 раза в день")
        elif stats["already_applied"] > 0:
            print("💡 На большинство подходящих вакансий уже подавали заявки")
        else:
            print("😕 Новые заявки не были отправлены")
            print("💡 Попробуйте изменить ключевые слова поиска или настройки")
