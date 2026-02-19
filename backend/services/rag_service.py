import openai
from typing import List, Dict
from core.config import get_settings

settings = get_settings()
openai.api_key = settings.openai_api_key

class RAGService:
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> Dict:
        relevant_chunks = [
            chunk for chunk in context_chunks 
            if chunk['similarity'] >= self.similarity_threshold
        ]
        
        if not relevant_chunks:
            return {
                'answer': "I couldn't find relevant information in your documents to answer this question.",
                'sources': []
            }
        
        context = "\n\n".join([
            f"[Document {chunk['document_id']}, Chunk {chunk['chunk_index']}]: {chunk['content']}"
            for chunk in relevant_chunks
        ])
        
        prompt = f"""Answer the question based strictly on the provided context.

Context:
{context}

Question: {query}

Answer:"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You answer questions based strictly on provided context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            sources = [
                {
                    'document_id': chunk['document_id'],
                    'chunk_index': chunk['chunk_index'],
                    'similarity_score': chunk['similarity']
                }
                for chunk in relevant_chunks
            ]
            
            return {'answer': answer, 'sources': sources}
            
        except Exception as e:
            return {'answer': f"Error: {str(e)}", 'sources': []}