import os
import uuid
import aiofiles
from datetime import datetime
from typing import Optional, List
from pymongo import DESCENDING
from app.core.database import get_database
from app.models.contract import Contract, ProcessingStatus, ContractListResponse, ContractStatusResponse
from app.services.ocr_service import ocr_service
from app.services.ai_service_robust import ai_service
import logging

logger = logging.getLogger(__name__)


class ContractService:
    def __init__(self):
        self.collection_name = "contracts"
    
    async def save_contract(self, contract: Contract) -> str:
        """save new contract to database"""
        db = get_database()
        collection = db[self.collection_name]
        
        contract_dict = contract.model_dump(by_alias=True, exclude={"id"})
        result = await collection.insert_one(contract_dict)
        return str(result.inserted_id)
    
    async def get_contract_by_id(self, contract_id: str) -> Optional[Contract]:
        """find contract by its contract_id"""
        db = get_database()
        collection = db[self.collection_name]
        
        document = await collection.find_one({"contract_id": contract_id})
        if document:
            document["_id"] = str(document["_id"])
            return Contract(**document)
        return None
    
    async def update_contract_status(self, contract_id: str, status: ProcessingStatus, 
                                   progress: float = None, error_details: str = None):
        """update the processing status of a contract"""
        db = get_database()
        collection = db[self.collection_name]
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if progress is not None:
            update_data["progress_percentage"] = progress
        
        if error_details:
            update_data["error_details"] = error_details
        
        # mark completion time when done
        if status == ProcessingStatus.COMPLETED:
            update_data["processed_at"] = datetime.utcnow()
        
        await collection.update_one(
            {"contract_id": contract_id},
            {"$set": update_data}
        )
    
    async def update_contract_data(self, contract_id: str, extracted_data, scoring, gap_analysis, raw_text: str):
        """save the extracted contract data after ai processing"""
        db = get_database()
        collection = db[self.collection_name]
        
        update_data = {
            "extracted_data": extracted_data.model_dump() if extracted_data else None,
            "scoring": scoring.model_dump() if scoring else None,
            "gap_analysis": gap_analysis.model_dump() if gap_analysis else None,
            "raw_text": raw_text,
            "updated_at": datetime.utcnow()
        }
        
        await collection.update_one(
            {"contract_id": contract_id},
            {"$set": update_data}
        )
    
    async def get_contracts(self, page: int = 1, limit: int = 10, 
                          status_filter: Optional[str] = None) -> ContractListResponse:
        """get paginated list of contracts with optional filtering"""
        db = get_database()
        collection = db[self.collection_name]
        
        # build the filter query
        filter_dict = {}
        if status_filter:
            filter_dict["status"] = status_filter
        
        # count total contracts
        total = await collection.count_documents(filter_dict)
        
        # calculate pagination stuff
        skip = (page - 1) * limit
        has_next = skip + limit < total
        has_prev = page > 1
        
        # get the actual contracts
        cursor = collection.find(filter_dict).sort("created_at", DESCENDING).skip(skip).limit(limit)
        contracts = []
        
        async for document in cursor:
            contract_status = ContractStatusResponse(
                contract_id=document["contract_id"],
                status=document["status"],
                progress_percentage=document.get("progress_percentage", 0.0),
                error_details=document.get("error_details"),
                created_at=document["created_at"],
                updated_at=document["updated_at"]
            )
            contracts.append(contract_status)
        
        return ContractListResponse(
            contracts=contracts,
            total=total,
            page=page,
            limit=limit,
            has_next=has_next,
            has_prev=has_prev
        )
    
    async def process_contract(self, contract_id: str, file_path: str):
        """main processing function - does ocr then ai analysis"""
        try:
            # start processing
            await self.update_contract_status(contract_id, ProcessingStatus.PROCESSING, 10.0)
            
            # first step: extract text with ocr
            logger.info(f"Starting OCR for contract {contract_id}")
            raw_text = await ocr_service.extract_text_from_pdf(file_path)
            
            if not raw_text:
                await self.update_contract_status(
                    contract_id, 
                    ProcessingStatus.FAILED, 
                    0.0,
                    "Failed to extract text from PDF"
                )
                return
            
            # halfway done
            await self.update_contract_status(contract_id, ProcessingStatus.PROCESSING, 50.0)
            
            # second step: analyze with ai
            logger.info(f"Starting AI analysis for contract {contract_id}")
            extracted_data, scoring, gap_analysis = await ai_service.parse_contract_text(raw_text)
            
            if not extracted_data:
                await self.update_contract_status(
                    contract_id, 
                    ProcessingStatus.FAILED, 
                    50.0,
                    "Failed to parse contract with AI"
                )
                return
            
            # almost done
            await self.update_contract_status(contract_id, ProcessingStatus.PROCESSING, 90.0)
            
            # save all the extracted data
            await self.update_contract_data(contract_id, extracted_data, scoring, gap_analysis, raw_text)
            
            # all done!
            await self.update_contract_status(contract_id, ProcessingStatus.COMPLETED, 100.0)
            
            logger.info(f"Successfully processed contract {contract_id}")
            
        except Exception as e:
            logger.error(f"Error processing contract {contract_id}: {e}")
            await self.update_contract_status(
                contract_id, 
                ProcessingStatus.FAILED, 
                0.0,
                f"Processing error: {str(e)}"
            )


# create the service instance
contract_service = ContractService()
