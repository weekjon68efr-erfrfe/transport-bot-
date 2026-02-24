"""Message templates for user responses"""
from datetime import datetime
from typing import Dict, Any
import textwrap


class Messages:
    """All message templates"""

    # Registration messages
    REGISTRATION_START = textwrap.dedent("""
    *Регистрация водителя*

    Добро пожаловать! Для начала работы нужно зарегистрироваться.

    Введите ваше ФИО (полное имя):
    """).strip()

    @staticmethod
    def registration_name_success(name: str) -> str:
        return textwrap.dedent(f"""
        ФИО: {name}

        Теперь введите ваш личный номер телефона:
        """).strip()

    @staticmethod
    def registration_phone_success() -> str:
        return "Введите номер вашей машины:"

    @staticmethod
    def registration_complete(name: str, phone: str, truck: str) -> str:
        return textwrap.dedent(f"""
        *Регистрация завершена!*

        *Ваши данные:*
        ФИО: {name}
        Телефон: +{phone}
        Машина: {truck}

        Отправьте *1* для заполнения нового груза
        Отправьте *0* для главного меню
        """).strip()

    # Menu messages
    @staticmethod
    def main_menu_unregistered() -> str:
        return textwrap.dedent("""
        Вы не зарегистрированы в системе.

        Отправьте *да* для регистрации
        """).strip()

    @staticmethod
    def main_menu_registered(name: str, truck: str) -> str:
        return textwrap.dedent(f"""
        Ваша машина: {truck}

        *Выберите действие:*
        1 - Новый отчет о взвешивании
        2 - Изменить номер машины
        3 - Переоформить регистрацию
        4 - Статистика
        0 - Главное меню
        """).strip()

    @staticmethod
    def statistics_menu() -> str:
        return textwrap.dedent("""
        Выберите период для статистики:
        1 - Сегодня
        2 - За 7 дней
        3 - За 30 дней
        4 - За всё время
        0 - Отмена / Главное меню
        """).strip()

    @staticmethod
    def statistics_report(stats: Dict[str, Any]) -> str:
        parts: list[str] = []

        # Drivers
        parts.append("*ВОДИТЕЛИ*\n")
        drivers = stats.get('by_driver') or []
        if drivers:
            for i, d in enumerate(drivers, start=1):
                name = (d.get('driver_name') or '').upper()
                phone = d.get('driver_phone') or ''
                cnt = d.get('count', 0)
                total = d.get('total', 0)
                parts.append(f"*{name}* {phone}:\nОтчётов: {cnt}. Суммарно {total:.0f} кг\n")
        else:
            parts.append("Нет данных по водителям.\n")

        # Trucks
        parts.append("*МАШИНЫ*\n")
        trucks = stats.get('by_truck') or []
        if trucks:
            for i, t in enumerate(trucks, start=1):
                truck = t.get('truck_number') or ''
                cnt = t.get('count', 0)
                total = t.get('total', 0)
                parts.append(f"{truck}:\nОтчётов: {cnt}. Суммарно {total:.0f} кг\n")
        else:
            parts.append("Нет данных по машинам.\n")

        # Clients
        parts.append("*КЛИЕНТЫ*\n")
        clients = stats.get('by_client') or []
        if clients:
            for i, c in enumerate(clients, start=1):
                client = c.get('client_name') or 'Неизвестный'
                cnt = c.get('count', 0)
                total = c.get('total', 0)
                parts.append(f"{client}:\nОтчётов: {cnt}. Суммарно {total:.0f} кг\n")
        else:
            parts.append("Нет данных по клиентам.\n")

        return "\n".join(parts).strip()

    # Report messages
    @staticmethod
    def enter_client() -> str:
        return "Введите имя клиента:"

    @staticmethod
    def enter_weight() -> str:
        return "Введите вес машины (в кг):"

    @staticmethod
    def enter_photo() -> str:
        return "Отправьте фотографию показаний весов для подтверждения"

    @staticmethod
    def invalid_number() -> str:
        return "Пожалуйста, введите число (например: 15000)"

    @staticmethod
    def negative_weight() -> str:
        return "Вес не может быть отрицательным. Пожалуйста, введите положительное число:"

    @staticmethod
    def confirmation_report(data: Dict[str, Any]) -> str:
        return textwrap.dedent(f"""
        *Подтверждение отчета*

        Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        Телефон: {data.get('driver_phone', '?')}
        Машина: {data.get('truck_number', '?')}
        Клиент: {data.get('client_name', '?')}

        Вес новый: {data.get('current_weight', 0):.0f} кг
        Вес предыдущий: {data.get('previous_weight', 0):.0f} кг
        Разница: {data.get('weight_difference', 0):+.0f} кг

        Напишите *да* для сохранения
        Напишите *нет* для отмены
        """).strip()

    @staticmethod
    def report_saved() -> str:
        return textwrap.dedent("""
        *Отчет сохранен и отправлен!*

        Отправьте *1* для заполнения нового груза
        Отправьте *0* для главного меню
        """).strip()

    @staticmethod
    def report_cancelled() -> str:
        return textwrap.dedent("""
        Отчет отменен.

        Отправьте *1* для нового отчета
        Отправьте *0* для главного меню
        """).strip()

    @staticmethod
    def truck_updated(truck: str) -> str:
        return f"Номер машины изменен на *{truck}*\n\nОтправьте *0* для главного меню"

    @staticmethod
    def unknown_command() -> str:
        return "Не понимаю команду. Отправьте *0* для меню"

    @staticmethod
    def error_occurred(error: str) -> str:
        return f"Произошла ошибка: {error}\n\nПожалуйста, попробуйте еще раз или отправьте *0*"
