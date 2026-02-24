"""
WhatsApp Green API client
"""
import requests
import re
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from config import Config
from utils.logger import logger


class WhatsAppError(Exception):
    """WhatsApp API error"""
    pass


class WhatsAppClient:
    """Green API client for WhatsApp"""
    
    def __init__(self):
        self.instance_id = Config.GREEN_API_ID_INSTANCE
        self.api_token = Config.GREEN_API_TOKEN_INSTANCE
        self.base_url = Config.GREEN_API_URL
        
        if not self.instance_id or not self.api_token:
            raise WhatsAppError("Green API credentials not configured")
        
        logger.info("✅ WhatsApp client initialized")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make API request with retries"""
        url = f"{self.base_url}/waInstance{self.instance_id}/{endpoint}/{self.api_token}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout: {endpoint}")
            raise WhatsAppError("API timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise WhatsAppError(f"API error: {str(e)}")
    
    def _format_chat_id(self, chat_id: str) -> str:
        """Ensure chat_id has proper suffix"""
        if not chat_id.endswith('@g.us') and not chat_id.endswith('@c.us'):
            return f"{chat_id}@c.us"
        return chat_id
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def send_message(self, chat_id: str, message: str) -> bool:
        """Send text message"""
        try:
            chat_id = self._format_chat_id(chat_id)
            
            # Split long messages
            if len(message) > 4000:
                parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for part in parts:
                    self._make_request('POST', 'sendMessage', {
                        "chatId": chat_id,
                        "message": part
                    })
            else:
                self._make_request('POST', 'sendMessage', {
                    "chatId": chat_id,
                    "message": message
                })
            
            logger.info(f"Message sent to {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2))
    def send_file_by_url(self, chat_id: str, url_file: str, file_name: str, caption: str = None) -> bool:
        """Send file by URL"""
        try:
            chat_id = self._format_chat_id(chat_id)
            
            data = {
                "chatId": chat_id,
                "urlFile": url_file,
                "fileName": file_name
            }
            
            if caption:
                data["caption"] = caption
            
            self._make_request('POST', 'sendFileByUrl', data)
            logger.info(f"File sent to {chat_id}: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send file to {chat_id}: {e}")
            return False
    
    def send_report(self, group_id: str, report_text: str, photo_url: str = None, photo_name: str = None) -> bool:
        """Send report to group with optional photo"""
        if not group_id:
            logger.error("GROUP_ID not configured")
            return False
        
        try:
            if photo_url and photo_name:
                # Send with photo
                return self.send_file_by_url(group_id, photo_url, photo_name, report_text)
            else:
                # Send text only
                return self.send_message(group_id, report_text)
                
        except Exception as e:
            logger.error(f"Failed to send report: {e}")
            return False
    
    def parse_webhook(self, data: Dict) -> Optional[Dict]:
        """Parse incoming webhook data"""
        try:
            webhook_type = data.get("typeWebhook")
            
            if webhook_type != "incomingMessageReceived":
                logger.debug(f"Ignoring webhook type: {webhook_type}")
                return None
            
            message_data = data.get("messageData", {})
            sender_data = data.get("senderData", {})
            
            chat_id = sender_data.get("chatId", "")
            # Normalize phone: take part before @ and keep only digits
            raw_phone = chat_id.split("@")[0]
            phone = re.sub(r"\D", "", raw_phone)
            
            # Check message type
            text = None
            has_media = False
            media_data = None
            
            if "textMessageData" in message_data:
                text = message_data["textMessageData"]["textMessage"]
            elif "extendedTextMessageData" in message_data:
                text = message_data["extendedTextMessageData"].get("text", "")
            elif any(key in message_data for key in ["imageMessageData", "photoMessageData", "fileMessageData"]):
                has_media = True
                media_data = message_data
                # Try to extract photo URL
                for key in ["imageMessageData", "photoMessageData", "fileMessageData"]:
                    if key in message_data:
                        media_data = message_data[key]
                        break
            else:
                logger.debug(f"Unknown message type: {message_data.keys()}")
                return None
            
            return {
                "phone": phone,
                "chat_id": chat_id,
                "text": text,
                "has_media": has_media,
                "media_data": media_data
            }
            
        except Exception as e:
            logger.error(f"Failed to parse webhook: {e}")
            return None