from pydantic import BaseModel
from datetime import datetime

class ChatEvent(BaseModel):
    event_id: str
    session_id: str
    user_id: str
    query: str
    response: str
    latency: float
    created_at: datetime