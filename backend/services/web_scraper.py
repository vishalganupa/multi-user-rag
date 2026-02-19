import re
import requests
from bs4 import BeautifulSoup
from typing import List

class WebScraper:
    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_url(self, url: str) -> str:
        """Extract text from website"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = soup.get_text()
            return text
        except Exception as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,!?;:()\-\'\"]', '', text)
        return text.strip()
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        words = text.split()
        chunks = []
        
        start = 0
        while start < len(words):
            end = start + self.chunk_size
            chunk = ' '.join(words[start:end])
            chunks.append(chunk)
            start = end - self.chunk_overlap
            if end >= len(words):
                break
        
        return chunks
    
    def process_url(self, url: str) -> List[str]:
        """Process URL and return chunks"""
        text = self.extract_text_from_url(url)
        cleaned_text = self.clean_text(text)
        chunks = self.chunk_text(cleaned_text)
        return chunks