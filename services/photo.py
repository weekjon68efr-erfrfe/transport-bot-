"""
Photo handling service
"""
import os
import hashlib
from datetime import datetime
from typing import Optional, Tuple
import requests
from PIL import Image
import io
import re
import numpy as np

try:
    import cv2
    import pytesseract
    _OCR_AVAILABLE = True
except Exception:
    cv2 = None
    pytesseract = None
    _OCR_AVAILABLE = False

from config import Config
from utils.logger import logger


class PhotoService:
    """Service for handling photos"""
    
    @staticmethod
    def download_photo(url: str, phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download photo from URL
        Returns: (success, filepath, error_message)
        """
        try:
            # Validate URL
            if not url or not url.startswith('http'):
                return False, None, "Invalid photo URL"
            
            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_phone = ''.join(c for c in phone if c.isdigit())
            filename = f"{safe_phone}_{timestamp}.jpg"
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            # Download with streaming
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check content length
            content_length = int(response.headers.get('content-length', 0))
            if content_length > Config.MAX_PHOTO_SIZE:
                return False, None, f"Photo too large (max {Config.MAX_PHOTO_SIZE//1024//1024}MB)"
            
            # Save file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify it's an image
            try:
                with Image.open(filepath) as img:
                    # Optionally resize if too large
                    if img.size[0] > 1920 or img.size[1] > 1080:
                        img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                        img.save(filepath, 'JPEG', quality=85)
            except Exception as e:
                os.remove(filepath)
                return False, None, "File is not a valid image"
            
            logger.info(f"Photo downloaded: {filepath}")
            return True, filepath, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download photo: {e}")
            return False, None, f"Download failed: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error downloading photo: {e}")
            return False, None, f"Error: {str(e)}"
    
    @staticmethod
    def get_photo_hash(filepath: str) -> Optional[str]:
        """Get SHA256 hash of photo"""
        try:
            sha256 = hashlib.sha256()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to hash photo: {e}")
            return None
    
    @staticmethod
    def cleanup_old_photos(days: int = 30):
        """Delete photos older than specified days"""
        try:
            now = datetime.now().timestamp()
            count = 0
            
            for filename in os.listdir(Config.UPLOAD_FOLDER):
                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    if now - file_time > days * 24 * 3600:
                        os.remove(filepath)
                        count += 1
            
            if count > 0:
                logger.info(f"Cleaned up {count} old photos")
                
        except Exception as e:
            logger.error(f"Failed to cleanup photos: {e}")

    @staticmethod
    def recognize_weight(filepath: str) -> Optional[float]:
        """Try to extract numeric weight from photo using OCR.
        Returns weight as float or None if not found/available.
        """
        if not _OCR_AVAILABLE:
            logger.debug("OCR libraries not available (pytesseract/opencv)")
            return None

        try:
            # Read image with OpenCV
            img = cv2.imdecode(np.fromfile(filepath, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                logger.debug("Failed to load image for OCR")
                return None

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Resize to improve OCR accuracy
            h, w = gray.shape
            scale = max(1, int(1000 / max(w, h)))
            if scale > 1:
                gray = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

            # Apply adaptive threshold to increase contrast
            gray = cv2.medianBlur(gray, 3)
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 31, 10)

            # Use pytesseract to read digits and separators only
            custom_oem_psm_config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789,.'"
            text = pytesseract.image_to_string(thresh, config=custom_oem_psm_config)

            if not text:
                return None

            # Find the largest numeric value in the OCR output
            matches = re.findall(r"\d+[\.,]?\d*", text)
            if not matches:
                return None

            # Choose the longest match (likely the weight) and parse
            best = max(matches, key=lambda s: len(s))
            weight_str = best.replace(',', '.').replace("'", '.')
            try:
                weight = float(weight_str)
                logger.info(f"OCR extracted weight: {weight} from {filepath}")
                return weight
            except ValueError:
                return None

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return None