from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import faiss
import pickle
import os

class VectorService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = 384
        self.user_indexes = {}
        self.user_chunks = {}
        self.index_dir = "./vector_indexes"
        os.makedirs(self.index_dir, exist_ok=True)
    
    def generate_embedding(self, text: str) -> np.ndarray:
        return self.model.encode(text)
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts)
    
    def get_user_index(self, user_id: int):
        if user_id not in self.user_indexes:
            index_path = f"{self.index_dir}/user_{user_id}.index"
            chunks_path = f"{self.index_dir}/user_{user_id}_chunks.pkl"
            
            if os.path.exists(index_path) and os.path.exists(chunks_path):
                self.user_indexes[user_id] = faiss.read_index(index_path)
                with open(chunks_path, 'rb') as f:
                    self.user_chunks[user_id] = pickle.load(f)
            else:
                self.user_indexes[user_id] = faiss.IndexFlatL2(self.dimension)
                self.user_chunks[user_id] = []
        
        return self.user_indexes[user_id]
    
    def add_document_chunks(self, user_id: int, document_id: int, chunks: List[str]):
        index = self.get_user_index(user_id)
        embeddings = self.generate_embeddings(chunks)
        index.add(embeddings.astype('float32'))
        
        if user_id not in self.user_chunks:
            self.user_chunks[user_id] = []
        
        for idx, chunk in enumerate(chunks):
            self.user_chunks[user_id].append({
                'document_id': document_id,
                'chunk_index': idx,
                'content': chunk
            })
        
        self._save_user_index(user_id)
    
    def search_similar(self, user_id: int, query: str, top_k: int = 3):
        if user_id not in self.user_indexes or len(self.user_chunks.get(user_id, [])) == 0:
            return []
        
        index = self.user_indexes[user_id]
        query_embedding = self.generate_embedding(query).astype('float32').reshape(1, -1)
        distances, indices = index.search(query_embedding, min(top_k, index.ntotal))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.user_chunks[user_id]):
                chunk_data = self.user_chunks[user_id][idx]
                similarity = 1 / (1 + dist)
                results.append({
                    'document_id': chunk_data['document_id'],
                    'chunk_index': chunk_data['chunk_index'],
                    'content': chunk_data['content'],
                    'similarity': float(similarity)
                })
        
        return results
    
    def _save_user_index(self, user_id: int):
        if user_id in self.user_indexes:
            index_path = f"{self.index_dir}/user_{user_id}.index"
            chunks_path = f"{self.index_dir}/user_{user_id}_chunks.pkl"
            
            faiss.write_index(self.user_indexes[user_id], index_path)
            with open(chunks_path, 'wb') as f:
                pickle.dump(self.user_chunks[user_id], f)