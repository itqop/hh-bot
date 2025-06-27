"""
🌐 Сервис для работы с браузером
"""

import time
import random
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import settings, AppConstants, UIFormatter
from ..models.vacancy import ApplicationResult

logger = logging.getLogger(__name__)


class BrowserInitializer:
    """Отвечает за инициализацию браузера"""

    @staticmethod
    def create_chrome_options(headless: bool) -> Options:
        """Создание опций Chrome"""
        options = Options()

        if headless:
            options.add_argument("--headless")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        return options

    @staticmethod
    def hide_automation(driver: webdriver.Chrome) -> None:
        """Скрытие признаков автоматизации"""
        try:
            driver.execute_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
            )
        except Exception as e:
            logger.warning(f"Не удалось скрыть признаки автоматизации: {e}")


class AuthenticationHandler:
    """Отвечает за процесс авторизации"""

    LOGIN_URL = f"{AppConstants.HH_SITE_URL}/account/login"

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def authenticate_interactive(self) -> bool:
        """Интерактивная авторизация на HH.ru"""
        try:
            logger.info("Переход на страницу авторизации...")
            self.driver.get(self.LOGIN_URL)

            print("\n🔐 РЕЖИМ РУЧНОЙ АВТОРИЗАЦИИ")
            print("1. Авторизуйтесь в браузере")
            print("2. Нажмите Enter для продолжения")

            input("⏳ Авторизуйтесь и нажмите Enter...")

            if self._check_authentication():
                logger.info("Авторизация успешна!")
                return True
            else:
                logger.error("Авторизация не завершена")
                return False

        except Exception as e:
            logger.error(f"Ошибка при авторизации: {e}")
            return False

    def _check_authentication(self) -> bool:
        """Проверка успешности авторизации"""
        try:
            current_url = self.driver.current_url
            page_text = self.driver.page_source.lower()

            success_indicators = [
                "applicant" in current_url,
                "account" in current_url and "login" not in current_url,
                "мои резюме" in page_text,
            ]

            return any(success_indicators)
        except Exception as e:
            logger.error(f"Ошибка проверки авторизации: {e}")
            return False


class VacancyApplicator:
    """Отвечает за подачу заявок на вакансии"""

    APPLY_SELECTORS = [
        '[data-qa="vacancy-response-link-top"]',
        '[data-qa="vacancy-response-button"]',
        '.bloko-button[data-qa*="response"]',
        'button[data-qa*="response"]',
        ".vacancy-response-link",
        'a[href*="response"]',
    ]

    ALREADY_APPLIED_INDICATORS = [
        "откликнулись",
        "отклик отправлен",
        "заявка отправлена",
        "response sent",
        "уже откликнулись",
        "чат",
    ]

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def apply_to_vacancy(self, vacancy_url: str, vacancy_name: str) -> ApplicationResult:
        """Подача заявки на вакансию"""
        try:
            truncated_name = UIFormatter.truncate_text(vacancy_name)
            logger.info(f"Переход к вакансии: {truncated_name}...")
            self.driver.get(vacancy_url)
            time.sleep(3)

            apply_button = self._find_apply_button()
            if not apply_button:
                return ApplicationResult(
                    vacancy_id="",
                    vacancy_name=vacancy_name,
                    success=False,
                    error_message="Кнопка отклика не найдена",
                )

            button_text = apply_button.text.lower()
            if self._is_already_applied(button_text):
                return ApplicationResult(
                    vacancy_id="",
                    vacancy_name=vacancy_name,
                    success=False,
                    already_applied=True,
                    error_message="Уже откликались на эту вакансию",
                )

            self.driver.execute_script("arguments[0].click();", apply_button)
            time.sleep(2)

            logger.info("Кнопка отклика нажата")
            return ApplicationResult(vacancy_id="", vacancy_name=vacancy_name, success=True)

        except Exception as e:
            logger.error(f"Ошибка при подаче заявки: {e}")
            return ApplicationResult(
                vacancy_id="",
                vacancy_name=vacancy_name,
                success=False,
                error_message=str(e),
            )

    def _find_apply_button(self):
        """Поиск кнопки отклика"""
        for selector in self.APPLY_SELECTORS:
            try:
                button = self.driver.find_element(By.CSS_SELECTOR, selector)
                return button
            except NoSuchElementException:
                continue
        return None

    def _is_already_applied(self, button_text: str) -> bool:
        """Проверка, не откликались ли уже"""
        return any(indicator in button_text for indicator in self.ALREADY_APPLIED_INDICATORS)


class BrowserService:
    """Главный сервис для управления браузером и автоматизации"""

    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self._is_authenticated = False
        self.auth_handler: Optional[AuthenticationHandler] = None
        self.applicator: Optional[VacancyApplicator] = None

    def initialize(self, headless: bool = None) -> bool:
        """Инициализация браузера"""
        if headless is None:
            headless = settings.browser.headless

        try:
            logger.info("Инициализация браузера...")

            options = BrowserInitializer.create_chrome_options(headless)
            service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, settings.browser.wait_timeout)

            self.auth_handler = AuthenticationHandler(self.driver)
            self.applicator = VacancyApplicator(self.driver)

            BrowserInitializer.hide_automation(self.driver)

            logger.info("Браузер успешно инициализирован")
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации браузера: {e}")
            return False

    def authenticate_interactive(self) -> bool:
        """Интерактивная авторизация на HH.ru"""
        if not self.driver or not self.auth_handler:
            logger.error("Браузер не инициализирован")
            return False

        success = self.auth_handler.authenticate_interactive()
        if success:
            self._is_authenticated = True
        return success

    def apply_to_vacancy(self, vacancy_url: str, vacancy_name: str) -> ApplicationResult:
        """Подача заявки на вакансию"""
        if not self.is_ready():
            return ApplicationResult(
                vacancy_id="",
                vacancy_name=vacancy_name,
                success=False,
                error_message="Браузер не готов или нет авторизации",
            )

        return self.applicator.apply_to_vacancy(vacancy_url, vacancy_name)

    def add_random_pause(self) -> None:
        """Случайная пауза между действиями"""
        try:
            pause_time = random.uniform(
                settings.application.pause_min, settings.application.pause_max
            )
            logger.info(f"Пауза {pause_time:.1f} сек...")
            time.sleep(pause_time)
        except Exception as e:
            logger.warning(f"Ошибка паузы: {e}")
            time.sleep(3)

    def close(self) -> None:
        """Закрытие браузера"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Браузер закрыт")
        except Exception as e:
            logger.warning(f"Ошибка при закрытии: {e}")
        finally:
            self.driver = None
            self.wait = None
            self._is_authenticated = False
            self.auth_handler = None
            self.applicator = None

    def is_ready(self) -> bool:
        """Проверка готовности к работе"""
        return self.driver is not None and self._is_authenticated and self.applicator is not None
