from pydantic import BaseModel
from datetime import datetime

class Temperature(BaseModel):
    last_temp: float
    next_temp: float
    current_time: datetime