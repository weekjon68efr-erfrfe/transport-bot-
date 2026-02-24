"""
Message templates for user responses
"""
from datetime import datetime
from typing import Optional, Dict, Any


class Messages:
    """All message templates"""
    
    # Registration messages
    REGISTRATION_START = """
*Регистрация водителя*

Добро пожаловать! Для начала работы нужно зарегистрироваться.

Введите ваше ФИО (полное имя):
"""
    
    @staticmethod
    def registration_name_success(name: str) -> str:
        return f"""ФИО: {name}

    Теперь введите ваш личный номер телефона:"""
    
    @staticmethod
    def registration_phone_success() -> str:
        return "Введите номер вашей машины:"
    
    @staticmethod
    def registration_complete(name: str, phone: str, truck: str) -> str:
        return f"""*Регистрация завершена!*

    *Ваши данные:*
    ФИО: {name}
    Телефон: +{phone}
    Машина: {truck}

    Отправьте *1* для заполнения нового груза
    Отправьте *0* для главного меню"""
    
    # Menu messages
    @staticmethod
    def main_menu_unregistered() -> str:
        return """Вы не зарегистрированы в системе.

    Отправьте *да* для регистрации"""
    
    @staticmethod
    def main_menu_registered(name: str, truck: str) -> str:
        return f"""Здравствуйте, {name}!
    Ваша машина: {truck}

    *Выберите действие:*
    1 - Новый отчет о взвешивании
    2 - Изменить номер машины
    3 - Переоформить регистрацию
    0 - Главное меню"""
    
    # Report messages
    @staticmethod
    def enter_client() -> str:
        return "Введите имя клиента:"
    
    @staticmethod
    def enter_weight() -> str:
        return "Введите вес машины (в кг):"
    
    @staticmethod
    def enter_photo() -> str:
        return """Отправьте фотографию показаний весов для подтверждения"""
    
    @staticmethod
    def invalid_number() -> str:
        return "Пожалуйста, введите число (например: 15000)"
    
    @staticmethod
    def negative_weight() -> str:
        return "Вес не может быть отрицательным. Пожалуйста, введите положительное число:"
    
    @staticmethod
    def confirmation_report(data: Dict[str, Any]) -> str:
        """Format confirmation report"""
        return f"""*Подтверждение отчета*

    Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}
    Телефон: {data.get('driver_phone', '?')}
    Машина: {data.get('truck_number', '?')}
    Клиент: {data.get('client_name', '?')}

    Вес новый: {data.get('current_weight', 0):.0f} кг
    Вес предыдущий: {data.get('previous_weight', 0):.0f} кг
    Разница: {data.get('weight_difference', 0):+.0f} кг

    Напишите *да* для сохранения
    Напишите *нет* для отмены"""
    
    @staticmethod
    def report_saved() -> str:
        return """*Отчет сохранен и отправлен!*

    Отправьте *1* для заполнения нового груза
    Отправьте *0* для главного меню"""
    
    @staticmethod
    def report_cancelled() -> str:
        return """Отчет отменен.

    Отправьте *1* для нового отчета
    Отправьте *0* для главного меню"""
    
    @staticmethod
    def truck_updated(truck: str) -> str:
        return f"Номер машины изменен на *{truck}*\n\nОтправьте *0* для главного меню"
    
    @staticmethod
    def unknown_command() -> str:
        return "Не понимаю команду. Отправьте *0* для меню"
    
    @staticmethod
    def error_occurred(error: str) -> str:
        return f"Произошла ошибка: {error}\n\nПожалуйста, попробуйте еще раз или отправьте *0*"