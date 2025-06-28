from ..core.job_application_manager import JobApplicationManager
from ..config.settings import settings, ResumeFileManager, UIFormatter


class CLIInterface:

    @staticmethod
    def print_welcome():
        print("🚀 HH.ru АВТОМАТИЗАЦИЯ v2.0")
        print(UIFormatter.create_separator())
        print("🏗️ Архитектурно правильная версия")
        print("🤖 С поддержкой Gemini AI")
        print("📄 Загрузка резюме из файлов")
        print(UIFormatter.create_separator())

    @staticmethod
    def print_settings_info():
        print("\n⚙️ ТЕКУЩИЕ НАСТРОЙКИ:")
        print(f"🔍 Ключевые слова: {settings.hh_search.keywords}")
        print(f"📊 Максимум заявок: {settings.application.max_applications}")
        ai_status = "✅ Доступен" if settings.enable_ai_matching() else "❌ Недоступен"
        print(f"🤖 Gemini AI: {ai_status}")
        browser_mode = "Фоновый" if settings.browser.headless else "Видимый"
        print(f"🌐 Режим браузера: {browser_mode}")

    @staticmethod
    def get_user_preferences():
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

        use_ai_cover_letters = True
        if settings.enable_ai_matching():
            cover_letter_choice = input("Использовать ИИ-сопроводительные письма? [y/n]: ").lower()
            use_ai_cover_letters = cover_letter_choice != "n"
        else:
            print("⚠️ ИИ-сопроводительные письма недоступны (нет GEMINI_API_KEY)")
            use_ai_cover_letters = False

        excludes = ", ".join(settings.get_exclude_keywords()[:5])
        print(f"\n🚫 Текущие исключения: {excludes}...")
        exclude_choice = input("Изменить список исключений? [y/n]: ").lower()
        if exclude_choice == "y":
            CLIInterface._configure_exclude_keywords()

        prompt = f"Максимум заявок [{settings.application.max_applications}]: "
        max_apps_input = input(prompt).strip()
        try:
            max_apps = (
                int(max_apps_input)
                if max_apps_input
                else settings.application.max_applications
            )
        except ValueError:
            max_apps = settings.application.max_applications

        return keywords, use_ai, use_ai_cover_letters, max_apps

    @staticmethod
    def _configure_exclude_keywords():
        print("\n⚙️ НАСТРОЙКА ИСКЛЮЧЕНИЙ:")
        print("Введите слова через запятую (или Enter для значений по умолчанию):")
        current_excludes = ", ".join(settings.get_exclude_keywords())
        print(f"Текущие: {current_excludes}")

        new_excludes = input("Новые исключения: ").strip()
        if new_excludes:
            exclude_list = [
                word.strip() for word in new_excludes.split(",") if word.strip()
            ]
            settings.get_exclude_keywords = lambda: exclude_list
            print(f"✅ Обновлены исключения: {exclude_list}")
        else:
            print("✅ Оставлены значения по умолчанию")

    @staticmethod
    def print_final_stats(stats):
        UIFormatter.print_section_header("📊 ИТОГОВАЯ СТАТИСТИКА:", long=True)

        if "error" in stats:
            print(f"❌ Ошибка: {stats['error']}")
        else:
            print(f"📝 Всего заявок: {stats['total_applications']}")
            print(f"✅ Успешных: {stats['successful']}")
            print(f"❌ Неудачных: {stats['failed']}")

            if "skipped" in stats and stats["skipped"] > 0:
                print(f"⏭️ Пропущено: {stats['skipped']}")

            if stats["successful"] > 0:
                print(f"\n🎉 Отлично! Отправлено {stats['successful']} заявок!")
            else:
                print("\n😕 Заявки не были отправлены")

        print(UIFormatter.create_separator(long=True))

    @staticmethod
    def run_application():
        try:
            cli = CLIInterface()

            cli.print_welcome()
            ResumeFileManager.create_sample_files()
            cli.print_settings_info()
            keywords, use_ai, use_ai_cover_letters, max_apps = cli.get_user_preferences()

            settings.update_search_keywords(keywords)
            settings.application.max_applications = max_apps
            settings.application.use_ai_cover_letters = use_ai_cover_letters

            print("\n🎯 ЗАПУСК С ПАРАМЕТРАМИ:")
            print(f"🔍 Поиск: {keywords}")
            print(f"🤖 AI: {'Включен' if use_ai else 'Отключен'}")
            print(f"📝 ИИ-письма: {'Включены' if use_ai_cover_letters else 'Отключены'}")
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
