from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List

# ==========================================
# User Schemas
# ==========================================

class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)  # ← FIXED: Added max_length
    
    @validator('password')
    def validate_password(cls, v):
        """Ensure password doesn't exceed bcrypt limit"""
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot exceed 72 bytes')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """Ensure username contains only valid characters"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response (excludes password)"""
    id: int
    email: str
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str


# ==========================================
# Document Schemas
# ==========================================

class DocumentUploadResponse(BaseModel):
    """Response after successful document upload"""
    id: int
    filename: str
    doc_type: str
    chunk_count: int
    upload_date: datetime
    
    class Config:
        from_attributes = True


class DocumentList(BaseModel):
    """Schema for listing documents"""
    id: int
    filename: str
    doc_type: str
    source_url: Optional[str] = None
    upload_date: datetime
    chunk_count: int
    
    class Config:
        from_attributes = True


class WebsiteIngest(BaseModel):
    """Schema for website URL ingestion"""
    url: str = Field(..., min_length=10, max_length=2000)
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


# ==========================================
# Chat Schemas
# ==========================================

class ChatQuery(BaseModel):
    """Schema for chat query"""
    query: str = Field(..., min_length=1, max_length=1000)
    
    @validator('query')
    def validate_query(cls, v):
        """Ensure query is not just whitespace"""
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()


class SourceInfo(BaseModel):
    """Information about a source document chunk"""
    document_name: str
    chunk_index: int
    similarity_score: float = Field(..., ge=0.0, le=1.0)  # Between 0 and 1


class ChatResponse(BaseModel):
    """Response from chat query"""
    answer: str
    sources: List[SourceInfo]
    timestamp: datetime


class ChatHistoryItem(BaseModel):
    """Single chat history item"""
    id: int
    query: str
    response: str
    sources: Optional[str] = None  # JSON string
    timestamp: datetime
    
    class Config:
        from_attributes = True


# ==========================================
# Error Response Schema
# ==========================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)