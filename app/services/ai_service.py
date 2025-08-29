import json
import asyncio
from typing import Optional, Dict, Any
from google import genai
from app.core.config import settings
from app.models.contract import ExtractedData, ScoringBreakdown, GapAnalysis
import logging

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        # Configure Google AI
        genai.configure(api_key=settings.google_ai_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Generation config for better structured output
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,  # Gemini supports much higher token limits
            response_mime_type="application/json"
        )
    
    async def parse_contract_text(self, text: str) -> tuple[Optional[ExtractedData], Optional[ScoringBreakdown], Optional[GapAnalysis]]:
        """Parse contract text using Google Gemini to extract structured data"""
        try:
            # Use a more efficient multi-step approach to stay within limits
            # Step 1: Extract basic information
            basic_data = await self._extract_basic_contract_data(text)
            if not basic_data:
                return None, None, None
                
            # Step 2: Extract financial and payment details
            financial_data = await self._extract_financial_data(text)
            
            # Step 3: Extract SLA and technical details
            technical_data = await self._extract_technical_data(text)
            
            # Step 4: Generate scoring and gap analysis
            scoring_data = await self._generate_scoring_and_gaps(text, basic_data, financial_data, technical_data)
            
            # Combine all data
            combined_data = self._combine_extracted_data(basic_data, financial_data, technical_data, scoring_data)
            
            if combined_data:
                extracted_data = ExtractedData(**combined_data["extracted_data"])
                scoring = ScoringBreakdown(**combined_data["scoring"])
                gap_analysis = GapAnalysis(**combined_data["gap_analysis"])
                return extracted_data, scoring, gap_analysis
            
            return None, None, None
                
        except Exception as e:
            logger.error(f"Error in AI parsing: {e}")
            return None, None, None
    
    async def _extract_basic_contract_data(self, text: str) -> Optional[Dict]:
        """Extract parties and account information"""
        prompt = f"""
Analyze this contract text and extract basic party and account information. Return ONLY a JSON object:

Contract Text (first 3000 chars):
{text[:3000]}

Required JSON structure:
{{
    "parties": [
        {{
            "name": "party name or null",
            "legal_entity_name": "legal entity or null", 
            "registration_details": "registration info or null",
            "authorized_signatories": ["list of signatories"],
            "roles": ["customer", "vendor", etc.],
            "confidence_score": 0.8
        }}
    ],
    "account_info": {{
        "billing_details": "billing address/details or null",
        "account_numbers": ["account numbers found"],
        "references": ["reference numbers"],
        "billing_contact": "billing contact or null",
        "technical_contact": "technical contact or null", 
        "confidence_score": 0.7
    }}
}}
"""
        return await self._make_ai_request(prompt)
    
    async def _extract_financial_data(self, text: str) -> Optional[Dict]:
        """Extract financial details and payment structure"""
        prompt = f"""
Analyze this contract text and extract financial and payment information. Return ONLY a JSON object:

Contract Text (searching for financial terms):
{text[:4000]}

Required JSON structure:
{{
    "financial_details": {{
        "line_items": [
            {{
                "description": "item description",
                "quantity": 1.0,
                "unit_price": 100.0,
                "total_price": 100.0,
                "confidence_score": 0.8
            }}
        ],
        "total_contract_value": 1000.0,
        "currency": "USD",
        "tax_information": "tax details or null",
        "additional_fees": ["list of fees"],
        "confidence_score": 0.8
    }},
    "payment_structure": {{
        "payment_terms": "Net 30",
        "payment_schedules": ["schedule details"],
        "due_dates": ["due dates"],
        "payment_methods": ["ACH", "Wire", etc.],
        "banking_details": "bank details or null",
        "confidence_score": 0.7
    }},
    "revenue_classification": {{
        "recurring_payments": true,
        "one_time_payments": false,
        "subscription_model": "monthly/annual/etc",
        "billing_cycles": ["monthly", "quarterly"],
        "renewal_terms": "renewal details",
        "auto_renewal": true,
        "confidence_score": 0.6
    }}
}}
"""
        return await self._make_ai_request(prompt)
    
    async def _extract_technical_data(self, text: str) -> Optional[Dict]:
        """Extract SLA and technical requirements"""
        prompt = f"""
Analyze this contract text and extract service level agreements and technical details. Return ONLY a JSON object:

Contract Text (searching for SLA terms):
{text[:4000]}

Required JSON structure:
{{
    "sla": {{
        "performance_metrics": ["99.9% uptime", "response times"],
        "benchmarks": ["performance benchmarks"],
        "penalty_clauses": ["penalties for non-compliance"],
        "remedies": ["available remedies"],
        "support_terms": "support details or null",
        "maintenance_terms": "maintenance details or null",
        "confidence_score": 0.5
    }}
}}
"""
        return await self._make_ai_request(prompt)
    
    async def _generate_scoring_and_gaps(self, text: str, basic_data: Dict, financial_data: Dict, technical_data: Dict) -> Optional[Dict]:
        """Generate scoring and gap analysis based on extracted data"""
        prompt = f"""
Based on the extracted contract data, generate scoring and gap analysis. Return ONLY a JSON object:

Extracted Data Summary:
- Parties: {len(basic_data.get('parties', [])) if basic_data else 0} found
- Financial: {"Yes" if financial_data and financial_data.get('financial_details') else "No"}
- Payment Terms: {"Yes" if financial_data and financial_data.get('payment_structure') else "No"}
- SLA: {"Yes" if technical_data and technical_data.get('sla') else "No"}
- Contacts: {"Yes" if basic_data and basic_data.get('account_info') else "No"}

Required JSON structure:
{{
    "scoring": {{
        "financial_completeness": 25.0,
        "party_identification": 20.0, 
        "payment_terms_clarity": 15.0,
        "sla_definition": 10.0,
        "contact_information": 8.0,
        "total_score": 78.0
    }},
    "gap_analysis": {{
        "missing_fields": ["list critical missing fields"],
        "low_confidence_fields": ["fields with confidence < 0.6"],
        "recommendations": ["actionable recommendations"]
    }}
}}

Scoring Guidelines (max points):
- Financial completeness: 30 points
- Party identification: 25 points  
- Payment terms clarity: 20 points
- SLA definition: 15 points
- Contact information: 10 points
"""
        return await self._make_ai_request(prompt)
    
    async def _make_ai_request(self, prompt: str) -> Optional[Dict]:
        """Make async request to Google AI"""
        try:
            # Run the blocking call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config
                )
            )
            
            if response and response.text:
                # Clean the response text
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                return json.loads(response_text.strip())
            
            return None
            
        except Exception as e:
            logger.error(f"Google AI request failed: {e}")
            return None
    
    def _combine_extracted_data(self, basic_data: Dict, financial_data: Dict, technical_data: Dict, scoring_data: Dict) -> Optional[Dict]:
        """Combine all extracted data into final structure"""
        try:
            combined = {
                "extracted_data": {
                    "parties": basic_data.get("parties", []) if basic_data else [],
                    "account_info": basic_data.get("account_info") if basic_data else None,
                    "financial_details": financial_data.get("financial_details") if financial_data else None,
                    "payment_structure": financial_data.get("payment_structure") if financial_data else None,
                    "revenue_classification": financial_data.get("revenue_classification") if financial_data else None,
                    "sla": technical_data.get("sla") if technical_data else None
                },
                "scoring": scoring_data.get("scoring") if scoring_data else {
                    "financial_completeness": 0.0,
                    "party_identification": 0.0,
                    "payment_terms_clarity": 0.0,
                    "sla_definition": 0.0,
                    "contact_information": 0.0,
                    "total_score": 0.0
                },
                "gap_analysis": scoring_data.get("gap_analysis") if scoring_data else {
                    "missing_fields": ["Unable to analyze due to processing error"],
                    "low_confidence_fields": [],
                    "recommendations": ["Retry contract processing"]
                }
            }
            
            return combined
            
        except Exception as e:
            logger.error(f"Error combining extracted data: {e}")
            return None


ai_service = AIService()
