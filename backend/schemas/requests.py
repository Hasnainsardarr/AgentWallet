"""Request schemas."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Browser session ID")
    message: str = Field(..., min_length=1, description="User message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123xyz",
                "message": "Create a new wallet"
            }
        }

