import requests
import aiofiles
import asyncio
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self):
        self.api_key = settings.ocr_space_api_key
        self.base_url = "https://api.ocr.space/parse/image"
    
    async def extract_text_from_pdf(self, file_path: str) -> Optional[str]:
        """extract text from pdf using ocr space api - this might take a while"""
        try:
            async with aiofiles.open(file_path, 'rb') as file:
                file_content = await file.read()
            
            # need to run the blocking request in a thread pool since ocr takes time
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.make_ocr_request, 
                file_content
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            return None
    
    def make_ocr_request(self, file_content: bytes) -> Optional[str]:
        """make the actual ocr request - this is the blocking part"""
        try:
            payload = {
                'apikey': self.api_key,
                'language': 'eng',
                'isOverlayRequired': False,
                'filetype': 'PDF',
                'detectOrientation': True,
                'isCreateSearchablePdf': False,
                'isSearchablePdfHideTextLayer': False,
                'scale': True,
                'isTable': True,  # better for contracts with tables
                'OCREngine': 2    # use engine 2 for better accuracy
            }
            
            files = {
                'file': ('contract.pdf', file_content, 'application/pdf')
            }
            
            response = requests.post(
                self.base_url,
                data=payload,
                files=files,
                timeout=60  # ocr can be slow
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('IsErroredOnProcessing'):
                error_msg = result.get('ErrorMessage', 'Unknown OCR error')
                logger.error(f"OCR processing error: {error_msg}")
                return None
            
            # extract text from all pages and combine
            extracted_text = ""
            parsed_results = result.get('ParsedResults', [])
            
            for page_result in parsed_results:
                page_text = page_result.get('ParsedText', '')
                extracted_text += page_text + "\n"
            
            return extracted_text.strip() if extracted_text.strip() else None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OCR API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in OCR request: {e}")
            return None


# create the ocr service instance
ocr_service = OCRService()
