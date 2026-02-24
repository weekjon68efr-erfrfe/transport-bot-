"""Message handlers for bot logic"""
from typing import Optional, Dict, Any
from datetime import datetime
import textwrap

from bot.states import UserState, MenuCommands, UserSession
from bot.messages import Messages
from bot.validators import Validators
from services.database import Database
from services.whatsapp import WhatsAppClient
from services.photo import PhotoService
from utils.logger import logger


class BotHandlers:
    """Main bot logic handlers"""
    
    def __init__(self):
        self.db = Database()
        self.whatsapp = WhatsAppClient()
        self.photo_service = PhotoService()
        
        # State handlers mapping
        self.state_handlers = {
            UserState.REGISTRATION_NAME: self.handle_registration_name,
            UserState.REGISTRATION_PHONE: self.handle_registration_phone,
            UserState.REGISTRATION_TRUCK: self.handle_registration_truck,
            UserState.AWAITING_CLIENT: self.handle_client_name,
            UserState.AWAITING_WEIGHT: self.handle_weight_input,
            UserState.AWAITING_PHOTO: self.handle_photo_input,
            UserState.AWAITING_CONFIRMATION: self.handle_confirmation,
            UserState.CHANGING_TRUCK: self.handle_change_truck,
        }
        
        logger.info("✅ Bot handlers initialized")
    
    def process_message(self, phone: str, text: str = None, 
                       has_media: bool = False, media_data: Dict = None) -> Optional[str]:
        """Main message processor"""
        try:
            # Check if user is registered
            driver = self.db.get_driver(phone)
            is_registered = driver and driver.get('is_registered', 0) == 1
            
            # Get current state
            state_data = self.db.get_user_state(phone)
            
            # Handle exit commands
            if text and MenuCommands.is_exit_command(text):
                return self.show_main_menu(phone, driver)
            
            # Handle registration commands
            if text == MenuCommands.RE_REGISTER:
                self.db.clear_user_state(phone)
                return self.start_registration(phone)
            
            # If not registered, force registration
            if not is_registered:
                return self.handle_unregistered_user(phone, text, state_data)
            
            # Registered user - check state
            if state_data:
                state_name = state_data['state']
                try:
                    state = UserState[state_name]
                    temp_data = state_data.get('temp_data', {})
                    
                    # Special handling for photo state
                    if state == UserState.AWAITING_PHOTO and has_media:
                        return self.handle_photo_received(phone, temp_data, media_data)
                    
                    # Get handler for current state
                    handler = self.state_handlers.get(state)
                    if handler:
                        return handler(phone, text, temp_data)
                        
                except KeyError:
                    logger.error(f"Invalid state: {state_name}")
                    self.db.clear_user_state(phone)
            
            # Handle menu commands
            if text == MenuCommands.NEW_REPORT:
                return self.start_new_report(phone, driver)
            elif text == MenuCommands.CHANGE_TRUCK:
                self.db.set_user_state(phone, UserState.CHANGING_TRUCK.name)
                return "Введите новый номер машины:"
            
            # Default response
            return self.show_main_menu(phone, driver)
            
        except Exception as e:
            logger.error(f"Error processing message from {phone}: {e}")
            return Messages.error_occurred(str(e))
    
    def handle_unregistered_user(self, phone: str, text: str, state_data: Dict) -> str:
        """Handle unregistered user"""
        if not state_data:
            return self.start_registration(phone)
        
        state_name = state_data['state']
        temp_data = state_data.get('temp_data', {})
        
        if state_name == UserState.REGISTRATION_NAME.name:
            return self.handle_registration_name(phone, text, temp_data)
        elif state_name == UserState.REGISTRATION_PHONE.name:
            return self.handle_registration_phone(phone, text, temp_data)
        elif state_name == UserState.REGISTRATION_TRUCK.name:
            return self.handle_registration_truck(phone, text, temp_data)
        
        return self.start_registration(phone)
    
    # ========== REGISTRATION HANDLERS ==========
    
    def start_registration(self, phone: str) -> str:
        """Start registration process"""
        self.db.set_user_state(phone, UserState.REGISTRATION_NAME.name)
        return Messages.REGISTRATION_START
    
    def handle_registration_name(self, phone: str, text: str, temp_data: Dict) -> str:
        """Handle name input during registration"""
        if not text:
            return "Пожалуйста, введите ваше ФИО"
        
        is_valid, result = Validators.validate_name(text)
        if not is_valid:
            return result
        
        temp_data['full_name'] = result
        self.db.set_user_state(
            phone, 
            UserState.REGISTRATION_PHONE.name,
            temp_data
        )
        
        return Messages.registration_name_success(result)
    
    def handle_registration_phone(self, phone: str, text: str, temp_data: Dict) -> str:
        """Handle phone input during registration"""
        if not text:
            return "Пожалуйста, введите ваш номер телефона"
        
        is_valid, result = Validators.validate_phone(text)
        if not is_valid:
            return result
        
        temp_data['personal_phone'] = result
        self.db.set_user_state(
            phone,
            UserState.REGISTRATION_TRUCK.name,
            temp_data
        )
        
        return Messages.registration_phone_success()
    
    def handle_registration_truck(self, phone: str, text: str, temp_data: Dict) -> str:
        """Handle truck number input during registration"""
        if not text:
            return "Пожалуйста, введите номер машины"
        
        is_valid, truck_number = Validators.validate_truck(text)
        if not is_valid:
            return truck_number
        
        # Complete registration
        full_name = temp_data.get('full_name', '')
        personal_phone = temp_data.get('personal_phone', '')
        
        success = self.db.register_driver(phone, full_name, personal_phone, truck_number)
        
        if success:
            self.db.clear_user_state(phone)
            return Messages.registration_complete(full_name, personal_phone, truck_number)
        else:
            return "Ошибка при регистрации. Пожалуйста, попробуйте еще раз."
    
    # ========== REPORT HANDLERS ==========
    
    def start_new_report(self, phone: str, driver: Dict) -> str:
        """Start new weighing report"""
        truck_number = driver.get('truck_number')
        
        if not truck_number:
            return "Номер машины не установлен. Сначала выполните пункт меню 2."
        
        temp_data = {
            'truck_number': truck_number,
            'driver_name': driver.get('full_name', ''),
            'driver_phone': driver.get('personal_phone', phone),
            'previous_weight': self.db.get_last_weight(truck_number)
        }
        
        self.db.set_user_state(phone, UserState.AWAITING_CLIENT.name, temp_data)
        return Messages.enter_client()
    
    def handle_client_name(self, phone: str, text: str, temp_data: Dict) -> str:
        """Handle client name input"""
        if not text or len(text.strip()) < 2:
            return "Пожалуйста, введите имя клиента (минимум 2 символа)"
        
        temp_data['client_name'] = text.strip()
        self.db.set_user_state(phone, UserState.AWAITING_WEIGHT.name, temp_data)
        
        return Messages.enter_weight()
    
    def handle_weight_input(self, phone: str, text: str, temp_data: Dict) -> str:
        """Handle weight input"""
        if not text:
            return Messages.enter_weight()
    
        is_valid, weight = Validators.validate_weight(text)
        
        if not is_valid:
            if weight is None:
                return Messages.invalid_number()
            else:
                return weight  # Error message from validator (negative weight)
        
        temp_data['current_weight'] = weight
        temp_data['weight_difference'] = weight - temp_data.get('previous_weight', 0)
        
        self.db.set_user_state(phone, UserState.AWAITING_PHOTO.name, temp_data)
        
        return Messages.enter_photo()
    
    def handle_photo_input(self, phone: str, text: str, temp_data: Dict) -> str:
        """Handle photo input (or skip)"""
        if text and text.lower() == MenuCommands.SKIP_PHOTO:
            # Skip photo
            temp_data['photo_received'] = False
            temp_data['photo_path'] = ''
            
            self.db.set_user_state(phone, UserState.AWAITING_CONFIRMATION.name, temp_data)
            
            return Messages.confirmation_report(temp_data)
        
        return Messages.enter_photo()
    
    def handle_photo_received(self, phone: str, temp_data: Dict, media_data: Dict) -> str:
        """Handle received photo"""
        # Extract photo URL
        photo_url = None
        if isinstance(media_data, dict):
            photo_url = media_data.get('downloadUrl') or media_data.get('url')
        
        if not photo_url:
            logger.error(f"No photo URL in media data: {media_data}")
            return "Не удалось получить фото. Попробуйте еще раз."
        
        # Download photo
        success, filepath, error = self.photo_service.download_photo(photo_url, phone)
        
        if not success:
            return f"{error}"
        
        # Update temp data
        temp_data['photo_received'] = True
        temp_data['photo_path'] = filepath
        temp_data['photo_url'] = photo_url
        
        self.db.set_user_state(phone, UserState.AWAITING_CONFIRMATION.name, temp_data)
        
        return Messages.confirmation_report(temp_data)
    
    def handle_confirmation(self, phone: str, text: str, temp_data: Dict) -> str:
        """Handle report confirmation"""
        if not text:
            return "Пожалуйста, напишите *да* для сохранения или *нет* для отмены"
        
        text_lower = text.lower()
        
        if text_lower in ['нет', 'no', 'н']:
            self.db.clear_user_state(phone)
            return Messages.report_cancelled()
        
        if text_lower not in ['да', 'yes', 'д', 'y']:
            return "Пожалуйста, напишите *да* для сохранения или *нет* для отмены"
        
        # Save report
        weighing_data = {
            'driver_phone': phone,
            'truck_number': temp_data['truck_number'],
            'driver_name': temp_data.get('driver_name', ''),
            'client_name': temp_data.get('client_name', ''),
            'current_weight': temp_data['current_weight'],
            'photo_path': temp_data.get('photo_path', ''),
            'station_name': ''
        }
        
        result = self.db.save_weighing(weighing_data)
        
        if result:
            # Send report to group
            self.send_report_to_group(phone, temp_data)
            
            self.db.clear_user_state(phone)
            return Messages.report_saved()
        else:
            return "Ошибка при сохранении отчета. Попробуйте еще раз."
    
    def handle_change_truck(self, phone: str, text: str, temp_data: Dict) -> str:
        """Handle truck number change"""
        if not text:
            return "Введите новый номер машины:"
        
        is_valid, truck_number = Validators.validate_truck(text)
        if not is_valid:
            return truck_number
        
        success = self.db.update_driver_truck(phone, truck_number)
        
        if success:
            self.db.clear_user_state(phone)
            return Messages.truck_updated(truck_number)
        else:
            return "Ошибка при обновлении номера машины"
    
    # ========== MENU ==========
    
    def show_main_menu(self, phone: str, driver: Dict = None) -> str:
        """Show main menu"""
        self.db.clear_user_state(phone)
        
        if not driver or not driver.get('is_registered'):
            return Messages.main_menu_unregistered()
        
        return Messages.main_menu_registered(
            driver.get('full_name', ''),
            driver.get('truck_number', '')
        )
    
    # ========== GROUP REPORT ==========
    
    def send_report_to_group(self, phone: str, temp_data: Dict):
        """Send report to WhatsApp group"""
        from config import Config
        
        if not Config.GROUP_ID:
            logger.warning("GROUP_ID not configured, report not sent")
            return
        
        driver_name = temp_data.get('driver_name', '') or ''
        driver_phone = temp_data.get('driver_phone', '') or ''

        report_text = textwrap.dedent(f"""
        *{driver_name.upper()}*  {driver_phone}

        Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}
        Машина: {temp_data.get('truck_number', '')}
        Клиент: {temp_data.get('client_name', '')}

        Вес новый: {temp_data.get('current_weight', 0):.0f} кг
        Вес предыдущий: {temp_data.get('previous_weight', 0):.0f} кг
        Разница: {temp_data.get('weight_difference', 0):+.0f} кг
        """).strip()
        
        photo_url = temp_data.get('photo_url')
        photo_name = None
        
        if photo_url and temp_data.get('photo_received'):
            photo_name = f"{temp_data['truck_number']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        self.whatsapp.send_report(
            Config.GROUP_ID,
            report_text,
            photo_url,
            photo_name
        )