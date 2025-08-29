from fastapi import APIRouter
from .contracts import router as contracts_router

api_router = APIRouter()
api_router.include_router(contracts_router)
