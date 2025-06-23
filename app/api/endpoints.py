from fastapi import APIRouter
from ..services.analysis import analyze_device_status

router = APIRouter()

@router.get("/status/{device_id}")
def get_status(device_id: int):
    return analyze_device_status(device_id)