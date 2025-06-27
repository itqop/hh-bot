"""
🖥️ Интерфейс командной строки для HH.ru автоматизации
"""

from ..core.job_application_manager import JobApplicationManager
from ..config.settings import settings, ResumeFileManager, UIFormatter


class CLIInterface:
    """Интерфейс командной строки"""

    @staticmethod
    def print_welcome():
        """Приветственное сообщение"""
        print("🚀 HH.ru АВТОМАТИЗАЦИЯ v2.0")
        print(UIFormatter.create_separator())
        print("🏗️ Архитектурно правильная версия")
        print("🤖 С поддержкой Gemini AI")
        print("📄 Загрузка резюме из файлов")
        print(UIFormatter.create_separator())

    @staticmethod
    def print_settings_info():
        """Информация о настройках"""
        print("\n⚙️ ТЕКУЩИЕ НАСТРОЙКИ:")
        print(f"🔍 Ключевые слова: {settings.hh_search.keywords}")
        print(f"📊 Максимум заявок: {settings.application.max_applications}")
        print(
            f"🤖 Gemini AI: "
            f"{'✅ Доступен' if settings.enable_ai_matching() else '❌ Недоступен'}"
        )
        print(f"🌐 Режим браузера: " f"{'Фоновый' if settings.browser.headless else 'Видимый'}")

    @staticmethod
    def get_user_preferences():
        """Получение предпочтений пользователя"""
        print("\n🎯 НАСТРОЙКА ПОИСКА:")

        keywords = input(f"Ключевые слова [{settings.hh_search.keywords}]: ").strip()
        if not keywords:
            keywords = settings.hh_search.keywords

        use_ai = True
        if settings.enable_ai_matching():
            ai_choice = input("Использовать AI фильтрацию? [y/n]: ").lower()
            use_ai = ai_choice != "n"
        else:
            print("⚠️ AI фильтрация недоступна (нет GEMINI_API_KEY)")
            use_ai = False

        max_apps_input = input(
            f"Максимум заявок [{settings.application.max_applications}]: "
        ).strip()
        try:
            max_apps = (
                int(max_apps_input) if max_apps_input else settings.application.max_applications
            )
        except ValueError:
            max_apps = settings.application.max_applications

        return keywords, use_ai, max_apps

    @staticmethod
    def print_final_stats(stats):
        """Вывод итоговой статистики"""
        UIFormatter.print_section_header("📊 ИТОГОВАЯ СТАТИСТИКА:", long=True)

        if "error" in stats:
            print(f"❌ Ошибка: {stats['error']}")
        else:
            print(f"📝 Всего заявок: {stats['total_applications']}")
            print(f"✅ Успешных: {stats['successful']}")
            print(f"❌ Неудачных: {stats['failed']}")

            if stats["successful"] > 0:
                print(f"\n🎉 Отлично! Отправлено {stats['successful']} заявок!")
            else:
                print("\n😕 Заявки не были отправлены")

        print(UIFormatter.create_separator(long=True))

    @staticmethod
    def run_application():
        """Главная функция запуска приложения"""
        try:
            cli = CLIInterface()

            cli.print_welcome()
            ResumeFileManager.create_sample_files()
            cli.print_settings_info()
            keywords, use_ai, max_apps = cli.get_user_preferences()

            settings.update_search_keywords(keywords)
            settings.application.max_applications = max_apps

            print("\n🎯 ЗАПУСК С ПАРАМЕТРАМИ:")
            print(f"🔍 Поиск: {keywords}")
            print(f"🤖 AI: {'Включен' if use_ai else 'Отключен'}")
            print(f"📊 Максимум заявок: {max_apps}")

            confirm = input("\nНачать автоматизацию? [y/n]: ").lower()
            if confirm != "y":
                print("❌ Отменено пользователем")
                return

            manager = JobApplicationManager()
            stats = manager.run_automation(keywords=keywords, use_ai=use_ai)
            cli.print_final_stats(stats)

        except KeyboardInterrupt:
            print("\n⏹️ Программа остановлена пользователем")
        except Exception as e:
            print(f"\n❌ Неожиданная ошибка: {e}")
        finally:
            print("\n👋 До свидания!")
