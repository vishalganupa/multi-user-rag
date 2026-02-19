import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import engine, Base
from api import auth_routes, document_routes, chat_routes

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multi-User RAG System",
    description="RAG system with user isolation",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_routes.router)
app.include_router(document_routes.router)
app.include_router(chat_routes.router)

@app.get("/")
async def root():
    return {"message": "Multi-User RAG System", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)# Make sure you're in backend folder with (venv) active