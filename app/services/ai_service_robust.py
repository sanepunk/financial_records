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
from app.models.contract import ExtractedData, ScoringBreakdown, GapAnalysis, SimpleParsedResult, ParsedExtractedFields


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
                "max_output_tokens": 8192,
                "response_mime_type": "application/json"
            }
            logger.info("Successfully configured Google AI (Gemini) for contract analysis")
        except Exception as e:
            logger.error(f"Failed to configure Google AI: {e}")
            raise RuntimeError(f"Failed to configure Google AI: {e}")
    
    async def parse_contract_text(self, text: str) -> tuple[Optional[ExtractedData], Optional[ScoringBreakdown], Optional[GapAnalysis]]:
        """main function to parse contract text using google ai"""
        try:
            return await self.parse_with_google_ai(text)
        except Exception as e:
            logger.error(f"Error in AI parsing: {e}")
            return None, None, None
    
    async def simple_parse_contract(self, text: str, file_id: str, file_path: str) -> Optional[SimpleParsedResult]:
        """simple parsing function for basic contract information"""
        try:
            prompt = self.build_simple_parsing_prompt(text)
            result = await self.call_google_ai_simple(prompt)
            
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
    
    async def parse_with_google_ai(self, text: str) -> tuple[Optional[ExtractedData], Optional[ScoringBreakdown], Optional[GapAnalysis]]:
        """parse using google ai with single comprehensive prompt"""
        try:
            prompt = self.build_contract_analysis_prompt(text)
            result = await self.call_google_ai(prompt)
            
            if result:
                # convert to pydantic models
                extracted_data = ExtractedData(**result["extracted_data"])
                scoring = ScoringBreakdown(**result["scoring"])
                gap_analysis = GapAnalysis(**result["gap_analysis"])
                return extracted_data, scoring, gap_analysis
            
            return None, None, None
                
        except Exception as e:
            logger.error(f"Error in Google AI parsing: {e}")
            return None, None, None
    
    def build_contract_analysis_prompt(self, text: str) -> str:
        """builds the prompt for contract analysis - this is where the magic happens"""
        return f"""
Analyze the following contract text and extract ALL relevant information. Return your response as a JSON object with the exact structure shown below. Assign confidence scores (0.0 to 1.0) for each extracted field.

Contract Text:
{text}

Return ONLY a valid JSON object with this exact structure:

{{
    "extracted_data": {{
        "parties": [
            {{
                "name": "string or null",
                "legal_entity_name": "string or null",
                "registration_details": "string or null",
                "authorized_signatories": ["list of strings"],
                "roles": ["customer", "vendor", "contractor"],
                "confidence_score": 0.8
            }}
        ],
        "account_info": {{
            "billing_details": "string or null",
            "account_numbers": ["list of account numbers"],
            "references": ["list of reference numbers"],
            "billing_contact": "string or null",
            "technical_contact": "string or null",
            "confidence_score": 0.7
        }},
        "financial_details": {{
            "line_items": [
                {{
                    "description": "string or null",
                    "quantity": 1.0,
                    "unit_price": 100.0,
                    "total_price": 100.0,
                    "confidence_score": 0.8
                }}
            ],
            "total_contract_value": 1000.0,
            "currency": "USD",
            "tax_information": "string or null",
            "additional_fees": ["list of fees"],
            "confidence_score": 0.8
        }},
        "payment_structure": {{
            "payment_terms": "Net 30",
            "payment_schedules": ["monthly", "quarterly"],
            "due_dates": ["2024-01-15"],
            "payment_methods": ["ACH", "Wire", "Check"],
            "banking_details": "string or null",
            "confidence_score": 0.7
        }},
        "revenue_classification": {{
            "recurring_payments": true,
            "one_time_payments": false,
            "subscription_model": "monthly",
            "billing_cycles": ["monthly", "annual"],
            "renewal_terms": "auto-renewal clause",
            "auto_renewal": true,
            "confidence_score": 0.6
        }},
        "sla": {{
            "performance_metrics": ["99.9% uptime", "4 hour response"],
            "benchmarks": ["performance standards"],
            "penalty_clauses": ["service credit penalties"],
            "remedies": ["available remedies"],
            "support_terms": "24/7 support",
            "maintenance_terms": "scheduled maintenance windows",
            "confidence_score": 0.5
        }}
    }},
    "scoring": {{
        "financial_completeness": 25.0,
        "party_identification": 20.0,
        "payment_terms_clarity": 15.0,
        "sla_definition": 10.0,
        "contact_information": 8.0,
        "total_score": 78.0
    }},
    "gap_analysis": {{
        "missing_fields": ["list of critical missing fields"],
        "low_confidence_fields": ["fields with confidence < 0.6"],
        "recommendations": ["specific actionable recommendations"]
    }}
}}

Scoring Guidelines (assign points based on completeness and clarity):
- Financial completeness (max 30 points): Line items, totals, currency, tax info
- Party identification (max 25 points): Clear party names, legal entities, signatories
- Payment terms clarity (max 20 points): Payment terms, schedules, methods
- SLA definition (max 15 points): Performance metrics, penalties, support terms
- Contact information (max 10 points): Billing and technical contacts

Gap Analysis Rules:
- Mark fields as missing if they are critical but not found in the contract
- Mark fields as low confidence if confidence score < 0.6
- Provide specific, actionable recommendations for improvement

Extract as much relevant information as possible from the contract text.
"""
    
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
    
    async def call_google_ai_simple(self, prompt: str) -> Optional[Dict]:
        """makes a simple call to google ai for basic parsing"""
        try:
            loop = asyncio.get_event_loop()
            simple_config = {
                "temperature": 0.1,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json"
            }
            
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config=simple_config
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
            logger.error(f"Google AI simple request failed: {e}")
            return None
    
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
