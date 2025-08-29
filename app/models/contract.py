from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    parsed_result: Optional[SimpleParsedResult] = None
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
