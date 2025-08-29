import json
import asyncio
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

try:
    from google import genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False
    logger.error("Google Generative AI not available - this is required for the service to work")

from app.core.config import settings
from app.models.contract import SimpleParsedResult, ParsedExtractedFields


class AIService:
    def __init__(self):
        # setup google ai - this is now required
        if not GOOGLE_AI_AVAILABLE:
            raise RuntimeError("Google Generative AI is required but not available. Please install: pip install google-generativeai")
        
        if not hasattr(settings, 'google_ai_api_key') or not settings.google_ai_api_key:
            raise RuntimeError("Google AI API key is required but not configured")
        
        try:
            self.client = genai.Client(api_key=settings.google_ai_api_key)
            self.generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json"
            }
            logger.info("Successfully configured Google AI (Gemini) for contract analysis")
        except Exception as e:
            logger.error(f"Failed to configure Google AI: {e}")
            raise RuntimeError(f"Failed to configure Google AI: {e}")
    
    async def parse_contract_text(self, text: str, file_id: str, file_path: str) -> Optional[SimpleParsedResult]:
        """main function to parse contract text using simple schema"""
        try:
            return await self.simple_parse_contract(text, file_id, file_path)
        except Exception as e:
            logger.error(f"Error in AI parsing: {e}")
            return None

    async def simple_parse_contract(self, text: str, file_id: str, file_path: str) -> Optional[SimpleParsedResult]:
        """simple parsing function for basic contract information"""
        try:
            prompt = self.build_simple_parsing_prompt(text)
            result = await self.call_google_ai(prompt)
            
            if result:
                # create the simple parsed result
                extracted_fields = ParsedExtractedFields(**result)
                return SimpleParsedResult(
                    file_id=file_id,
                    file_path=file_path,
                    status="parsed",
                    extracted_fields=extracted_fields
                )
            
            return None
                
        except Exception as e:
            logger.error(f"Error in simple AI parsing: {e}")
            return None
    
    def build_simple_parsing_prompt(self, text: str) -> str:
        """builds a simple prompt for basic contract information extraction"""
        return f"""
Analyze the following contract text and extract the basic information. Return your response as a JSON object with the exact structure shown below.

Contract Text:
{text}

Return ONLY a valid JSON object with this exact structure:

{{
    "party_a": "First party name (individual or company)",
    "party_b": "Second party name (individual or company)", 
    "effective_date": "Contract start date (YYYY-MM-DD format if found)",
    "expiry_date": "Contract end date (YYYY-MM-DD format if found)",
    "contract_value": "Total contract value with currency symbol"
}}

Instructions:
- Extract the main parties involved in the contract
- Find start and end dates in YYYY-MM-DD format if possible
- Include currency symbol with the contract value (₹, $, €, etc.)
- If any field is not found, return null for that field
- Keep party names concise but complete
"""
    
    async def call_google_ai(self, prompt: str) -> Optional[Dict]:
        """makes the actual call to google ai - runs in thread since it's blocking"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config=self.generation_config
                )
            )
            
            if response and response.text:
                response_text = response.text.strip()
                # clean up markdown formatting if present
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                return json.loads(response_text.strip())
            
            return None
            
        except Exception as e:
            logger.error(f"Google AI request failed: {e}")
            return None


# create the service instance
ai_service = AIService()
