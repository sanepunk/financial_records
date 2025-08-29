from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PartyInfo(BaseModel):
    name: Optional[str] = None
    legal_entity_name: Optional[str] = None
    registration_details: Optional[str] = None
    authorized_signatories: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    confidence_score: float = 0.0


class AccountInfo(BaseModel):
    billing_details: Optional[str] = None
    account_numbers: Optional[List[str]] = None
    references: Optional[List[str]] = None
    billing_contact: Optional[str] = None
    technical_contact: Optional[str] = None
    confidence_score: float = 0.0


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    confidence_score: float = 0.0


class FinancialDetails(BaseModel):
    line_items: List[LineItem] = []
    total_contract_value: Optional[float] = None
    currency: Optional[str] = None
    tax_information: Optional[str] = None
    additional_fees: Optional[List[str]] = None
    confidence_score: float = 0.0


class PaymentStructure(BaseModel):
    payment_terms: Optional[str] = None
    payment_schedules: Optional[List[str]] = None
    due_dates: Optional[List[str]] = None
    payment_methods: Optional[List[str]] = None
    banking_details: Optional[str] = None
    confidence_score: float = 0.0


class RevenueClassification(BaseModel):
    recurring_payments: Optional[bool] = None
    one_time_payments: Optional[bool] = None
    subscription_model: Optional[str] = None
    billing_cycles: Optional[List[str]] = None
    renewal_terms: Optional[str] = None
    auto_renewal: Optional[bool] = None
    confidence_score: float = 0.0


class ServiceLevelAgreement(BaseModel):
    performance_metrics: Optional[List[str]] = None
    benchmarks: Optional[List[str]] = None
    penalty_clauses: Optional[List[str]] = None
    remedies: Optional[List[str]] = None
    support_terms: Optional[str] = None
    maintenance_terms: Optional[str] = None
    confidence_score: float = 0.0


class ExtractedData(BaseModel):
    parties: List[PartyInfo] = []
    account_info: Optional[AccountInfo] = None
    financial_details: Optional[FinancialDetails] = None
    payment_structure: Optional[PaymentStructure] = None
    revenue_classification: Optional[RevenueClassification] = None
    sla: Optional[ServiceLevelAgreement] = None


class ScoringBreakdown(BaseModel):
    financial_completeness: float = 0.0  # 30 points max
    party_identification: float = 0.0    # 25 points max
    payment_terms_clarity: float = 0.0   # 20 points max
    sla_definition: float = 0.0          # 15 points max
    contact_information: float = 0.0     # 10 points max
    total_score: float = 0.0             # 100 points max


class GapAnalysis(BaseModel):
    missing_fields: List[str] = []
    low_confidence_fields: List[str] = []
    recommendations: List[str] = []


class Contract(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    contract_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress_percentage: float = 0.0
    error_details: Optional[str] = None
    extracted_data: Optional[ExtractedData] = None
    scoring: Optional[ScoringBreakdown] = None
    gap_analysis: Optional[GapAnalysis] = None
    raw_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ContractUploadResponse(BaseModel):
    contract_id: str
    message: str
    status: ProcessingStatus


class ContractStatusResponse(BaseModel):
    contract_id: str
    status: ProcessingStatus
    progress_percentage: float
    error_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ContractListResponse(BaseModel):
    contracts: List[ContractStatusResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


# Simple parsed result schema
class ParsedExtractedFields(BaseModel):
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    contract_value: Optional[str] = None


class SimpleParsedResult(BaseModel):
    file_id: str
    file_path: str
    status: str = "parsed"
    extracted_fields: ParsedExtractedFields
