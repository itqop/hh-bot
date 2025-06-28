import time
import random
import logging
import json
from typing import Optional
from pathlib import Path
from enum import Enum
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from ..config.settings import settings, AppConstants, UIFormatter
from ..models.vacancy import ApplicationResult

class SubmissionResult(Enum):
    SUCCESS = "success"
    FAILED = "failed" 
    SKIPPED = "skipped"

logger = logging.getLogger(__name__)


class SessionManager:
    """Управление сессиями авторизации HH.ru"""

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.session_dir = Path("session_data")
        self.cookies_file = self.session_dir / "hh_cookies.json"
        self.session_dir.mkdir(exist_ok=True)

    def save_session(self) -> bool:
        """Сохранение текущей сессии в файл"""
        try:
            cookies = self.driver.get_cookies()
            session_data = {
                "cookies": cookies,
                "user_agent": self.driver.execute_script("return navigator.userAgent;"),
                "timestamp": time.time(),
            }

            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Сессия сохранена в {self.cookies_file}")
            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения сессии: {e}")
            return False

    def load_session(self) -> bool:
        """Загрузка сохраненной сессии"""
        try:
            if not self.cookies_file.exists():
                logger.info("Файл сессии не найден")
                return False

            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            if not self._is_session_valid(session_data):
                logger.info("Сессия устарела или невалидна")
                return False

            self.driver.get(AppConstants.HH_SITE_URL)
            time.sleep(2)

            for cookie in session_data["cookies"]:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Не удалось добавить cookie: {e}")

            logger.info("Сессия загружена из файла")
            return True

        except Exception as e:
            logger.error(f"Ошибка загрузки сессии: {e}")
            return False

    def clear_session(self) -> None:
        """Удаление сохраненной сессии"""
        try:
            if self.cookies_file.exists():
                self.cookies_file.unlink()
                logger.info("Сессия удалена")
        except Exception as e:
            logger.warning(f"Ошибка удаления сессии: {e}")

    def _is_session_valid(self, session_data: dict) -> bool:
        """Проверка валидности сессии по времени"""
        try:
            session_age = time.time() - session_data.get("timestamp", 0)
            max_age = 7 * 24 * 3600  # 7 дней
            return session_age < max_age
        except Exception:
            return False


class BrowserInitializer:
    """Отвечает за инициализацию браузера"""

    @staticmethod
    def create_chrome_options(headless: bool) -> Options:
        options = Options()

        if headless:
            options.add_argument("--headless")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VoiceInteraction")
        options.add_argument("--disable-speech-api")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--log-level=3")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_experimental_option("excludeSwitches", ["disable-logging"])

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
        self.session_manager = SessionManager(driver)

    def authenticate_interactive(self) -> bool:
        """Интерактивная авторизация на HH.ru с поддержкой сохраненной сессии"""
        try:
            print("\n🔐 ПРОВЕРКА СОХРАНЕННОЙ СЕССИИ")
            logger.info("Проверяем сохраненную сессию...")
            
            if self.session_manager.load_session():
                self.driver.refresh()
                time.sleep(3)
                
                if self._check_authentication():
                    print("✅ Использована сохраненная сессия")
                    logger.info("Авторизация через сохраненную сессию успешна!")
                    return True
                else:
                    print("❌ Сохраненная сессия недействительна")
                    logger.warning("Сохраненная сессия недействительна")
                    self.session_manager.clear_session()

            print("\n🔐 РЕЖИМ РУЧНОЙ АВТОРИЗАЦИИ")
            print("1. Авторизуйтесь в браузере")
            print("2. Нажмите Enter для продолжения")
            print("3. Сессия будет сохранена для повторного использования")

            logger.info("Переход на страницу авторизации...")
            self.driver.get(self.LOGIN_URL)

            input("⏳ Авторизуйтесь и нажмите Enter...")

            if self._check_authentication():
                logger.info("Авторизация успешна!")
                
                if self.session_manager.save_session():
                    print("✅ Сессия сохранена для следующих запусков")
                else:
                    print("⚠️ Не удалось сохранить сессию")
                
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

    def apply_to_vacancy(
        self, vacancy_url: str, vacancy_name: str
    ) -> ApplicationResult:
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

            logger.info("Кнопка отклика нажата, ищем форму заявки...")
            
            submit_result = self._submit_application_form()
            
            if submit_result == SubmissionResult.SUCCESS:
                logger.info("✅ Заявка успешно отправлена")
                return ApplicationResult(
                    vacancy_id="", vacancy_name=vacancy_name, success=True
                )
            elif submit_result == SubmissionResult.SKIPPED:
                logger.warning("⚠️ Вакансия пропущена (нет модального окна)")
                return ApplicationResult(
                    vacancy_id="",
                    vacancy_name=vacancy_name,
                    success=False,
                    skipped=True,
                    error_message="Модальное окно не найдено (возможно тестовая вакансия)",
                )
            else:  # FAILED
                logger.warning("❌ Не удалось отправить заявку в модальном окне")
                return ApplicationResult(
                    vacancy_id="",
                    vacancy_name=vacancy_name,
                    success=False,
                    error_message="Ошибка отправки в модальном окне",
                )

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
        return any(
            indicator in button_text for indicator in self.ALREADY_APPLIED_INDICATORS
        )

    def _submit_application_form(self) -> SubmissionResult:
        """Отправка заявки в модальном окне"""
        try:
            modal_selectors = [
                '[data-qa="modal-overlay"]',
                '.magritte-modal-overlay',
                '[data-qa="modal"]',
                '[data-qa="vacancy-response-popup"]',
                '.vacancy-response-popup',
                '.modal',
                '.bloko-modal',
            ]
            
            submit_selectors = [
                '[data-qa="vacancy-response-submit-popup"]',
                'button[form="RESPONSE_MODAL_FORM_ID"]',
                'button[type="submit"][form="RESPONSE_MODAL_FORM_ID"]',
                '[data-qa="vacancy-response-letter-submit"]',
                'button[data-qa*="submit"]',
                'button[type="submit"]',
                'input[type="submit"]',
                '.bloko-button[data-qa*="submit"]',
            ]

            modal_found = False
            for selector in modal_selectors:
                try:
                    modal = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if modal:
                        modal_found = True
                        logger.info(f"Модальное окно найдено: {selector}")
                        break
                except Exception:
                    continue

            if not modal_found:
                logger.warning("⚠️ Модальное окно не найдено - пропускаем вакансию (возможно тестовая или ошибка)")
                return SubmissionResult.SKIPPED

            form_selectors = [
                'form[name="vacancy_response"]',
                'form[id="RESPONSE_MODAL_FORM_ID"]',
                'form[data-qa*="response"]',
            ]
            
            form_found = False
            for form_selector in form_selectors:
                try:
                    form = self.driver.find_element(By.CSS_SELECTOR, form_selector)
                    if form:
                        form_found = True
                        logger.info(f"Форма отклика найдена: {form_selector}")
                        break
                except Exception:
                    continue
                    
            if not form_found:
                logger.warning("Форма отклика не найдена в модальном окне - пропускаем")
                return SubmissionResult.SKIPPED

            time.sleep(1)

            for selector in submit_selectors:
                try:
                    submit_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if submit_button:
                        logger.info(f"Нажимаем кнопку отправки: {submit_button.text.strip()}")
                        self.driver.execute_script("arguments[0].click();", submit_button)
                        time.sleep(3)
                        if self._check_success_message():
                            return SubmissionResult.SUCCESS
                        else:
                            return SubmissionResult.FAILED
                except Exception:
                    continue

            logger.warning("Кнопка отправки в модальном окне не найдена")
            return SubmissionResult.FAILED

        except Exception as e:
            logger.error(f"Ошибка в модальном окне: {e}")
            return SubmissionResult.FAILED

    def _check_success_message(self) -> bool:
        """Проверка успешной отправки заявки"""
        try:
            success_indicators = [
                "отклик отправлен",
                "заявка отправлена", 
                "успешно отправлено",
                "спасибо за отклик",
                "ваш отклик получен",
                "response sent",
                "отклик на вакансию отправлен",
                "резюме отправлено",
                "откликнулись на вакансию",
            ]
            
            success_selectors = [
                '[data-qa*="success"]',
                '[data-qa*="sent"]',
                '.success-message',
                '.response-sent',
                '[class*="success"]',
            ]
            
            for selector in success_selectors:
                try:
                    success_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if success_element and success_element.is_displayed():
                        logger.info(f"Найден элемент успеха: {selector} - {success_element.text}")
                        return True
                except Exception:
                    continue
            
            page_text = self.driver.page_source.lower()
            
            for indicator in success_indicators:
                if indicator in page_text:
                    logger.info(f"Найдено подтверждение: '{indicator}'")
                    return True
            
            current_url = self.driver.current_url
            if "sent" in current_url or "success" in current_url or "response" in current_url:
                logger.info(f"URL указывает на успешную отправку: {current_url}")
                return True
                
            modal_disappeared = True
            try:
                self.driver.find_element(By.CSS_SELECTOR, '[data-qa="modal-overlay"]')
                modal_disappeared = False
            except NoSuchElementException:
                pass
                
            if modal_disappeared:
                logger.info("Модальное окно исчезло - возможно отклик отправлен")
                return True
                
            logger.info("Подтверждение отправки не найдено")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки успеха: {e}")
            return False


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

    def apply_to_vacancy(
        self, vacancy_url: str, vacancy_name: str
    ) -> ApplicationResult:
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
        return (
            self.driver is not None
            and self._is_authenticated
            and self.applicator is not None
        )
