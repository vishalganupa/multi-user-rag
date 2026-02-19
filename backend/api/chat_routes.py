from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json

from core.database import get_db
from core.config import get_settings
from core.dependencies import get_current_user
from models.database_models import User, Document, ChatHistory
from schemas.api_schemas import ChatQuery, ChatResponse, ChatHistoryItem, SourceInfo
from services.vector_service import VectorService
from services.rag_service import RAGService

settings = get_settings()
router = APIRouter(prefix="/api/chat", tags=["Chat"])

vector_service = VectorService(settings.embedding_model)
rag_service = RAGService(settings.similarity_threshold)


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    query: ChatQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a chat query using RAG"""
    
    try:
        # Search for similar chunks
        similar_chunks = vector_service.search_similar(
            user_id=current_user.id,
            query=query.query,
            top_k=settings.top_k
        )
        
        # Generate answer using RAG
        result = rag_service.generate_answer(query.query, similar_chunks)
        
        # Get document names for sources
        sources_with_names = []
        for source in result['sources']:
            document = db.query(Document).filter(
                Document.id == source['document_id']
            ).first()
            
            if document:
                sources_with_names.append(SourceInfo(
                    document_name=document.filename,
                    chunk_index=source['chunk_index'],
                    similarity_score=source['similarity_score']
                ))
        
        # Save to chat history
        chat_record = ChatHistory(
            user_id=current_user.id,
            query=query.query,
            response=result['answer'],
            # Fixed: Use model_dump() instead of dict() for Pydantic v2
            sources=json.dumps([s.model_dump() for s in sources_with_names])
        )
        
        db.add(chat_record)
        db.commit()
        db.refresh(chat_record)
        
        return ChatResponse(
            answer=result['answer'],
            sources=sources_with_names,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        db.rollback()
        print(f"Chat query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


@router.get("/history", response_model=List[ChatHistoryItem])
async def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get chat history for current user"""
    
    try:
        history = db.query(ChatHistory).filter(
            ChatHistory.user_id == current_user.id
        ).order_by(ChatHistory.timestamp.desc()).limit(limit).all()
        
        return history
        
    except Exception as e:
        print(f"Failed to fetch chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.delete("/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear chat history for current user"""
    
    try:
        deleted_count = db.query(ChatHistory).filter(
            ChatHistory.user_id == current_user.id
        ).delete()
        
        db.commit()
        
        return {
            "message": "Chat history cleared successfully",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        db.rollback()
        print(f"Failed to clear chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )