from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os

class RAGSystem:
    def __init__(self, document_content: str = None):
        self.model = SentenceTransformer('all-MiniLM-L6-v2') # Smaller, faster model for quick testing
        self.documents = []
        self.embeddings = None
        self.index = None
        if document_content:
            self._process_document_content(document_content)

    def _process_document_content(self, content: str):
        """Processes text content to create chunks and embeddings."""
        # Simple chunking: split by sentences. For real-world, use more advanced chunking.
        self.documents = [s.strip() for s in content.split('.') if s.strip()]
        
        if not self.documents:
            print("No usable content found for RAG system.")
            return

        print(f"Processing {len(self.documents)} document chunks for RAG...")
        self.embeddings = self.model.encode(self.documents, show_progress_bar=False) # No progress bar in Streamlit for cleaner UI
        
        # Create a FAISS index for efficient similarity search
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension) 
        self.index.add(np.array(self.embeddings).astype('float32'))
        print("RAG system initialized with embeddings.")

    def retrieve_context(self, query: str, top_k: int = 3) -> str:
        """Retrieves the most relevant document chunks for a given query."""
        if not self.index:
            return "No knowledge base loaded for RAG."

        query_embedding = self.model.encode([query])
        
        # Perform similarity search
        distances, indices = self.index.search(np.array(query_embedding).astype('float32'), top_k)
        
        retrieved_texts = [self.documents[idx] for idx in indices[0]]
        
        # Combine retrieved texts into a single context string
        context = "\n".join(retrieved_texts)
        return context

    def get_rag_prompt(self, query: str) -> str:
        """Constructs a prompt for the LLM with retrieved context."""
        context = self.retrieve_context(query)
        if context == "No knowledge base loaded for RAG.":
            return query # Fallback if no RAG context available

        prompt = (
            f"You are an assistant trained to answer questions using the given context. "
            f"If the answer is not in the context, state that you don't have enough information.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n"
            f"Answer:"
        )
        return prompt