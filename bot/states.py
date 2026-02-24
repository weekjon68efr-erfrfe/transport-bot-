"""
Finite state machine for user dialogues
"""
from enum import Enum, auto
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class UserState(Enum):
    """Possible user states"""
    # Registration states
    REGISTRATION_NAME = auto()
    REGISTRATION_PHONE = auto()
    REGISTRATION_TRUCK = auto()
    
    # Report states
    AWAITING_CLIENT = auto()
    AWAITING_WEIGHT = auto()
    AWAITING_PHOTO = auto()
    AWAITING_CONFIRMATION = auto()
    
    # Settings states
    CHANGING_TRUCK = auto()
    # Statistics
    AWAITING_STATS_PERIOD = auto()


class MenuCommands:
    """Menu command constants"""
    MAIN_MENU = "0"
    NEW_REPORT = "1"
    CHANGE_TRUCK = "2"
    RE_REGISTER = "3"
    STATISTICS = "4"
    
    CONFIRM_YES = "да"
    CONFIRM_NO = "нет"
    SKIP_PHOTO = "пропустить"
    
    @classmethod
    def is_exit_command(cls, text: str) -> bool:
        """Check if text is exit command"""
        return text.lower() in [cls.MAIN_MENU, "меню"]


@dataclass
class UserSession:
    """User session data"""
    phone: str
    state: UserState
    step: Optional[str] = None
    temp_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage"""
        return {
            'phone': self.phone,
            'state': self.state.name,
            'step': self.step,
            'temp_data': self.temp_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create from dict"""
        return cls(
            phone=data['phone'],
            state=UserState[data['state']],
            step=data.get('step'),
            temp_data=data.get('temp_data', {})
        )