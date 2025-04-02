from datetime import datetime
from typing import Dict, List, Any
from pydantic import BaseModel

class CryptoAgentSchema(BaseModel):
    """Schema for storing crypto analysis results."""
    timestamp: str
    coin_id: str
    timeframe: str
    real_time: bool
    data: Dict[str, Any]
    analysis: str

class CryptoAgentSchemaLog(BaseModel):
    """Schema for storing multiple crypto analysis logs."""
    agent_name: str
    agent_description: str
    logs: List[CryptoAgentSchema] 