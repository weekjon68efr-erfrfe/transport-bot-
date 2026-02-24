"""
Input validators
"""
import re
import os
from typing import Optional, Tuple


class Validators:
    """Input validation methods"""
    
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, Optional[str]]:
        """Validate full name"""
        name = name.strip()
        if len(name) < 3:
            return False, "Имя должно содержать минимум 3 символа"
        if len(name) > 100:
            return False, "Имя слишком длинное (максимум 100 символов)"
        if not re.match(r'^[а-яА-Яa-zA-Z\s\-]+$', name):
            return False, "Имя может содержать только буквы, пробелы и дефисы"
        return True, name
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """Validate phone number"""
        # Extract digits
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) < 10:
            return False, "Номер телефона должен содержать минимум 10 цифр"
        if len(digits) > 15:
            return False, "Номер телефона слишком длинный"
        
        return True, digits
    
    @staticmethod
    def validate_truck(truck: str) -> Tuple[bool, Optional[str]]:
        """Validate truck number"""
        truck = truck.strip().upper()
        
        if len(truck) < 3:
            return False, "Номер машины должен содержать минимум 3 символа"
        if len(truck) > 20:
            return False, "Номер машины слишком длинный"
        
        # Basic format: letters and numbers
        if not re.match(r'^[А-ЯA-Z0-9\-\s]+$', truck):
            return False, "Номер может содержать буквы, цифры, пробелы и дефисы"
        
        return True, truck
    
    @staticmethod
    def validate_weight(weight_str: str) -> Tuple[bool, Optional[float]]:
        """
        Validate weight input
        Now only checks if it's a valid number, no min/max limits
        """
        # Remove spaces and replace comma with dot
        weight_str = weight_str.strip().replace(',', '.').replace(' ', '')
        
        try:
            weight = float(weight_str)
            
            # Only check if it's positive (can't have negative weight)
            if weight < 0:
                return False, "⚠️ Вес не может быть отрицательным"
            
            return True, weight
            
        except ValueError:
            return False, None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove any path components
        filename = os.path.basename(filename)
        # Keep only safe characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        return filename