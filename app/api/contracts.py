import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
from typing import Optional
# import magic
from app.core.config import settings
from app.models.contract import (
    Contract, ContractUploadResponse, ContractStatusResponse, 
    ContractListResponse, ProcessingStatus, SimpleParsedResult
)
from app.services.contract_service import contract_service
from app.services.ai_service_robust import ai_service
from app.services.ocr_service import ocr_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts", tags=["contracts"])


# make sure upload folder exists
os.makedirs(settings.upload_dir, exist_ok=True)


@router.post("/upload", response_model=ContractUploadResponse)
async def upload_contract(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """upload a contract file and start processing it"""
    try:
        # basic validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # check file size - don't want huge files
        if file.size > settings.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {settings.max_file_size / 1024 / 1024:.1f}MB"
            )
        
        # read file to check what type it is
        content = await file.read()
        await file.seek(0)  # reset file pointer
        
        # make sure its a pdf
        # mime_type = magic.from_buffer(content, mime=True)
        # if mime_type != 'application/pdf':
        #     raise HTTPException(
        #         status_code=400, 
        #         detail="Only PDF files are supported"
        #     )
        
        # generate unique ids and paths
        contract_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{contract_id}{file_extension}"
        file_path = os.path.join(settings.upload_dir, filename)
        
        # save the file to disk
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # create database record
        contract = Contract(
            contract_id=contract_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file.size,
            mime_type='application/pdf',
            status=ProcessingStatus.PENDING
        )
        
        # save to database
        await contract_service.save_contract(contract)
        
        # start processing in background using fastapi background tasks
        background_tasks.add_task(contract_service.process_contract, contract_id, file_path)
        
        logger.info(f"Contract {contract_id} uploaded and queued for processing")
        
        return ContractUploadResponse(
            contract_id=contract_id,
            message="Contract uploaded successfully and queued for processing",
            status=ProcessingStatus.PENDING
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading contract: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}/status", response_model=ContractStatusResponse)
async def get_contract_status(contract_id: str):
    """check how the contract processing is going"""
    try:
        contract = await contract_service.get_contract_by_id(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        return ContractStatusResponse(
            contract_id=contract.contract_id,
            status=contract.status,
            progress_percentage=contract.progress_percentage,
            error_details=contract.error_details,
            created_at=contract.created_at,
            updated_at=contract.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contract status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}")
async def get_contract_data(contract_id: str):
    """get the full contract data - only works when processing is done"""
    try:
        contract = await contract_service.get_contract_by_id(contract_id)
        
        if not contract:
            logger.warning(f"Contract {contract_id} not found in database")
            raise HTTPException(status_code=404, detail="Contract not found")
        
        logger.info(f"Contract {contract_id} found with status: {contract.status}")
        
        if contract.status != ProcessingStatus.COMPLETED:
            logger.warning(f"Contract {contract_id} processing not complete. Current status: {contract.status}")
            raise HTTPException(
                status_code=400, 
                detail=f"Contract processing not complete. Current status: {contract.status}"
            )
        
        return contract
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contract data for {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=ContractListResponse)
async def get_contracts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """get list of contracts with pagination and filtering"""
    try:
        # validate status filter if provided
        if status and status not in [s.value for s in ProcessingStatus]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {[s.value for s in ProcessingStatus]}"
            )
        
        return await contract_service.get_contracts(page, limit, status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contracts list: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}/download")
async def download_contract(contract_id: str):
    """download the original contract file"""
    try:
        contract = await contract_service.get_contract_by_id(contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        if not os.path.exists(contract.file_path):
            raise HTTPException(status_code=404, detail="Contract file not found")
        
        return FileResponse(
            path=contract.file_path,
            filename=contract.filename,
            media_type=contract.mime_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading contract: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/simple-parse", response_model=SimpleParsedResult)
async def simple_parse_contract(file: UploadFile = File(...)):
    """simple contract parsing - returns basic information quickly"""
    try:
        # basic validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # check file size
        if file.size > settings.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size is {settings.max_file_size / 1024 / 1024:.1f}MB"
            )
        
        # read file content
        content = await file.read()
        
        # generate file id for this parsing session
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        temp_filename = f"temp_{file_id}{file_extension}"
        temp_file_path = os.path.join(settings.upload_dir, temp_filename)
        
        # save temporarily for OCR processing
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(content)
        
        try:
            # extract text using OCR
            logger.info(f"Starting OCR for simple parsing of {file.filename}")
            raw_text = await ocr_service.extract_text_from_pdf(temp_file_path)
            
            if not raw_text:
                raise HTTPException(status_code=400, detail="Failed to extract text from PDF")
            
            # simple AI parsing
            logger.info(f"Starting simple AI parsing for {file.filename}")
            parsed_result = await ai_service.simple_parse_contract(raw_text, file_id, file.filename)
            
            if not parsed_result:
                raise HTTPException(status_code=500, detail="Failed to parse contract")
            
            logger.info(f"Successfully parsed contract {file.filename}")
            return parsed_result
            
        finally:
            # clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simple contract parsing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
