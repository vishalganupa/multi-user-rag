from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
from urllib.parse import urlparse

from core.database import get_db
from core.config import get_settings
from core.dependencies import get_current_user
from models.database_models import User, Document, DocumentChunk
from schemas.api_schemas import DocumentUploadResponse, DocumentList, WebsiteIngest
from services.pdf_processor import PDFProcessor
from services.web_scraper import WebScraper
from services.vector_service import VectorService

settings = get_settings()
router = APIRouter(prefix="/api/documents", tags=["Documents"])

pdf_processor = PDFProcessor(settings.chunk_size, settings.chunk_overlap)
web_scraper = WebScraper(settings.chunk_size, settings.chunk_overlap)
vector_service = VectorService(settings.embedding_model)

os.makedirs(settings.upload_dir, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process PDF document"""
    
    # Validate file extension (case-insensitive)
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum of {settings.max_file_size / (1024*1024):.1f}MB"
        )
    
    # Validate file is not empty
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    try:
        # Process PDF
        chunks = pdf_processor.process_pdf(content)
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from PDF. File may be empty or corrupted."
            )
        
        # Create document record
        db_document = Document(
            user_id=current_user.id,
            filename=file.filename,
            doc_type='pdf',
            chunk_count=len(chunks)
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Store chunks in database
        for idx, chunk_content in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=db_document.id,
                chunk_index=idx,
                content=chunk_content,
                embedding_id=f"{db_document.id}_{idx}"
            )
            db.add(chunk)
        
        db.commit()
        
        # Add to vector store
        try:
            vector_service.add_document_chunks(current_user.id, db_document.id, chunks)
        except Exception as vector_error:
            # Rollback database if vector storage fails
            db.rollback()
            print(f"Vector storage failed: {vector_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create document embeddings"
            )
        
        return db_document
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Document upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.post("/ingest-website", response_model=DocumentUploadResponse)
async def ingest_website(
    website: WebsiteIngest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ingest content from website URL"""
    
    # Validate URL format
    try:
        parsed_url = urlparse(website.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")
        
        if parsed_url.scheme not in ['http', 'https']:
            raise ValueError("Only HTTP/HTTPS URLs are supported")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    try:
        # Scrape website
        chunks = web_scraper.process_url(website.url)
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from website. Page may be empty or inaccessible."
            )
        
        domain = parsed_url.netloc
        
        # Create document record
        db_document = Document(
            user_id=current_user.id,
            filename=f"Web: {domain}",
            doc_type='web',
            source_url=website.url,
            chunk_count=len(chunks)
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Store chunks
        for idx, chunk_content in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=db_document.id,
                chunk_index=idx,
                content=chunk_content,
                embedding_id=f"{db_document.id}_{idx}"
            )
            db.add(chunk)
        
        db.commit()
        
        # Add to vector store
        try:
            vector_service.add_document_chunks(current_user.id, db_document.id, chunks)
        except Exception as vector_error:
            db.rollback()
            print(f"Vector storage failed: {vector_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create document embeddings"
            )
        
        return db_document
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Website ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest website: {str(e)}"
        )


@router.get("/", response_model=List[DocumentList])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for current user"""
    try:
        documents = db.query(Document).filter(
            Document.user_id == current_user.id
        ).order_by(Document.upload_date.desc()).all()
        
        return documents
    except Exception as e:
        print(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and its embeddings"""
    
    # Find document with user ownership check
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you don't have permission to delete it"
        )
    
    try:
        # Delete from database (cascades to chunks)
        db.delete(document)
        db.commit()
        
        # Note: Vector store cleanup would go here if implemented
        # vector_service.delete_document_chunks(current_user.id, document_id)
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id,
            "filename": document.filename
        }
        
    except Exception as e:
        db.rollback()
        print(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )