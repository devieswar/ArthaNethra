"""
Chat Session model for managing conversations with documents
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatSession(BaseModel):
    """A chat session with associated documents"""
    
    id: str = Field(..., description="Unique session identifier")
    name: str = Field(..., description="Session name")
    document_ids: List[str] = Field(default_factory=list, description="Documents in this session")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = Field(default=0, description="Number of messages in this session")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "session_123",
                "name": "Financial Analysis Q4 2023",
                "document_ids": ["doc_abc", "doc_def"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "message_count": 15
            }
        }


class ChatMessage(BaseModel):
    """A message in a chat session"""
    
    id: str = Field(..., description="Unique message identifier")
    session_id: str = Field(..., description="Chat session ID")
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_123",
                "session_id": "session_123",
                "role": "user",
                "content": "What are the key financial risks?",
                "created_at": "2024-01-01T12:00:00Z"
            }
        }

