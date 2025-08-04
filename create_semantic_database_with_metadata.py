"""
Create semantic database from NCGA JSON files with metadata preservation.
This script processes articles, policy content, and evidence content separately,
maintaining their metadata for better search filtering and context.
"""

import os
import json
from typing import List, Dict
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NCGASemanticDatabase:
    def __init__(self, persist_directory="chroma_db_metadata"):
        self.persist_directory = persist_directory
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv('OPENAI_API_KEY'),
            model_name="text-embedding-ada-002"
        )
        self.chunk_size = 500  # Smaller chunks to stay under token limits
        self.chunk_overlap = 100
        
    def load_articles(self, filepath="ncga_articles.json") -> List[Dict]:
        """Load and process articles with metadata"""
        print(f"\nLoading articles from {filepath}...")
        
        with open(filepath, 'r') as f:
            articles = json.load(f)
        
        documents = []
        for article in articles:
            # Create document with full metadata
            doc = {
                'content': f"{article['title']}\n\n{article['content']}",
                'metadata': {
                    'type': 'news',
                    'category': 'article',
                    'title': article['title'],
                    'url': article.get('link', ''),
                    'pub_date': article.get('pub_date', ''),
                    'article_number': article.get('article_number', 0),
                    'source': 'NCGA Articles'
                }
            }
            documents.append(doc)
        
        print(f"Loaded {len(documents)} articles")
        return documents
    
    def load_policy_content(self, filepath="ncga_policy_content.json") -> List[Dict]:
        """Load and process policy content with metadata"""
        print(f"\nLoading policy content from {filepath}...")
        
        with open(filepath, 'r') as f:
            policies = json.load(f)
        
        documents = []
        for policy in policies:
            # Create document with policy metadata
            doc = {
                'content': policy['cleaned_evidence_content'],
                'metadata': {
                    'type': 'policy',
                    'category': 'policy_document',
                    'title': policy['title'],
                    'url': policy.get('url', ''),
                    'source': 'NCGA Policy Documents'
                }
            }
            documents.append(doc)
        
        print(f"Loaded {len(documents)} policy sections")
        return documents
    
    def load_evidence_content(self, filepath="ncga_cleaned_evidence_content.json") -> List[Dict]:
        """Load and process evidence content with metadata"""
        print(f"\nLoading evidence content from {filepath}...")
        
        with open(filepath, 'r') as f:
            evidence_data = json.load(f)
        
        documents = []
        for evidence in evidence_data:
            # Determine if this is more policy-like or general content
            page_name = evidence.get('page_name', '').lower()
            is_policy_related = any(term in page_name for term in ['policy', 'position', 'advocacy', 'priority'])
            
            # Use the cleaned evidence content which is most refined
            content = evidence.get('cleaned_evidence_content', 
                                 evidence.get('extracted_content', 
                                            evidence.get('original_content', '')))
            
            doc = {
                'content': content,
                'metadata': {
                    'type': 'policy' if is_policy_related else 'general',
                    'category': 'evidence_content',
                    'title': evidence['title'],
                    'url': evidence.get('url', ''),
                    'page_name': evidence.get('page_name', ''),
                    'original_length': evidence.get('original_length', 0),
                    'cleaned_length': evidence.get('cleaned_length', 0),
                    'source': 'NCGA Evidence Content'
                }
            }
            documents.append(doc)
        
        print(f"Loaded {len(documents)} evidence documents")
        return documents
    
    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """Split documents into chunks while preserving metadata"""
        print(f"\nChunking {len(documents)} documents...")
        
        chunks = []
        for doc in documents:
            content = doc['content']
            metadata = doc['metadata']
            
            # Simple text splitting - split on paragraphs first, then by size
            text_chunks = self._split_text(content)
            
            # Add chunk-specific metadata
            for i, chunk_text in enumerate(text_chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = i
                chunk_metadata['total_chunks'] = len(text_chunks)
                
                chunk = {
                    'content': chunk_text,
                    'metadata': chunk_metadata
                }
                chunks.append(chunk)
        
        print(f"Created {len(chunks)} chunks")
        return chunks
    
    def _split_text(self, text: str) -> List[str]:
        """Simple text splitting function"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        # Split on double newlines first (paragraphs)
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) + 2 > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Paragraph itself is too long, split it
                    if len(paragraph) > self.chunk_size:
                        # Split long paragraph by sentences or words
                        words = paragraph.split(' ')
                        temp_chunk = ""
                        for word in words:
                            if len(temp_chunk) + len(word) + 1 <= self.chunk_size:
                                temp_chunk += " " + word if temp_chunk else word
                            else:
                                if temp_chunk:
                                    chunks.append(temp_chunk.strip())
                                temp_chunk = word
                        if temp_chunk:
                            current_chunk = temp_chunk
                    else:
                        current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def create_vector_store(self, chunks: List[Dict]):
        """Create or update the vector store with chunks"""
        print(f"\nCreating vector store with {len(chunks)} chunks...")
        
        # Create or get collection
        collection = self.client.get_or_create_collection(
            name="ncga_documents",
            embedding_function=self.openai_ef
        )
        
        # Prepare data for ChromaDB - truncate very long content to stay under token limits
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            content = chunk['content']
            # Truncate extremely long content (roughly 4 chars per token)
            max_chars = 6000  # ~1500 tokens to be safe
            if len(content) > max_chars:
                content = content[:max_chars] + "..."
                print(f"  Truncated chunk {i} from {len(chunk['content'])} to {len(content)} chars")
            
            documents.append(content)
            metadatas.append(chunk['metadata'])
            ids.append(f"doc_{i}")
        
        # Add documents to collection in batches (OpenAI embedding limits)
        batch_size = 20  # Very small batches to avoid token limits
        for i in range(0, len(documents), batch_size):
            end_idx = min(i + batch_size, len(documents))
            print(f"Adding batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
            
            collection.add(
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )
        
        print(f"Vector store created and persisted to {self.persist_directory}")
        return collection
    
    def create_database(self):
        """Main method to create the semantic database"""
        print("Creating NCGA Semantic Database with Metadata...")
        print("="*60)
        
        # Load all document types
        all_documents = []
        
        # Load articles (news)
        if os.path.exists("ncga_articles.json"):
            all_documents.extend(self.load_articles())
        
        # Load policy content
        if os.path.exists("ncga_policy_content.json"):
            all_documents.extend(self.load_policy_content())
        
        # Load evidence content (mixed policy/general)
        if os.path.exists("ncga_cleaned_evidence_content.json"):
            all_documents.extend(self.load_evidence_content())
        
        if not all_documents:
            print("No documents found to process!")
            return
        
        # Chunk all documents
        chunks = self.chunk_documents(all_documents)
        
        # Print statistics
        print("\nDocument Statistics:")
        print("-"*40)
        news_count = sum(1 for chunk in chunks if chunk['metadata']['type'] == 'news')
        policy_count = sum(1 for chunk in chunks if chunk['metadata']['type'] == 'policy')
        general_count = sum(1 for chunk in chunks if chunk['metadata']['type'] == 'general')
        
        print(f"News chunks: {news_count}")
        print(f"Policy chunks: {policy_count}")
        print(f"General chunks: {general_count}")
        print(f"Total chunks: {len(chunks)}")
        
        # Create vector store
        self.create_vector_store(chunks)
        
        print("\n✅ Database creation complete!")
        print("\nYou can now use metadata filters in your searches:")
        print("  - filter={'type': 'news'} for news articles")
        print("  - filter={'type': 'policy'} for policy content")
        print("  - filter={'type': 'general'} for general content")


if __name__ == "__main__":
    # Delete existing database to start fresh
    import shutil
    if os.path.exists("chroma_db_metadata"):
        print("Deleting existing database...")
        shutil.rmtree("chroma_db_metadata")
    
    # Create new database
    db_creator = NCGASemanticDatabase()
    db_creator.create_database()