"""
🚀 HH.ru Автоматизация - Entry point для python -m hh_bot
"""

from .cli import CLIInterface


def main():
    """Главная функция"""
    CLIInterface.run_application()


if __name__ == "__main__":
    main()
