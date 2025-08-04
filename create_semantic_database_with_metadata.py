"""
Create semantic database from NCGA JSON files with metadata preservation.
This script processes articles, policy content, and evidence content separately,
maintaining their metadata for better search filtering and context.
"""

import os
import json
from typing import List, Dict
from datetime import datetime
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NCGASemanticDatabase:
    def __init__(self, persist_directory="chroma_db_metadata"):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
    def load_articles(self, filepath="ncga_articles.json") -> List[Document]:
        """Load and process articles with metadata"""
        print(f"\nLoading articles from {filepath}...")
        
        with open(filepath, 'r') as f:
            articles = json.load(f)
        
        documents = []
        for article in articles:
            # Create document with full metadata
            doc = Document(
                page_content=f"{article['title']}\n\n{article['content']}",
                metadata={
                    'type': 'news',
                    'category': 'article',
                    'title': article['title'],
                    'url': article.get('link', ''),
                    'pub_date': article.get('pub_date', ''),
                    'article_number': article.get('article_number', 0),
                    'source': 'NCGA Articles'
                }
            )
            documents.append(doc)
        
        print(f"Loaded {len(documents)} articles")
        return documents
    
    def load_policy_content(self, filepath="ncga_policy_content.json") -> List[Document]:
        """Load and process policy content with metadata"""
        print(f"\nLoading policy content from {filepath}...")
        
        with open(filepath, 'r') as f:
            policies = json.load(f)
        
        documents = []
        for policy in policies:
            # Create document with policy metadata
            doc = Document(
                page_content=policy['cleaned_evidence_content'],
                metadata={
                    'type': 'policy',
                    'category': 'policy_document',
                    'title': policy['title'],
                    'url': policy.get('url', ''),
                    'source': 'NCGA Policy Documents'
                }
            )
            documents.append(doc)
        
        print(f"Loaded {len(documents)} policy sections")
        return documents
    
    def load_evidence_content(self, filepath="ncga_cleaned_evidence_content.json") -> List[Document]:
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
            
            doc = Document(
                page_content=content,
                metadata={
                    'type': 'policy' if is_policy_related else 'general',
                    'category': 'evidence_content',
                    'title': evidence['title'],
                    'url': evidence.get('url', ''),
                    'page_name': evidence.get('page_name', ''),
                    'original_length': evidence.get('original_length', 0),
                    'cleaned_length': evidence.get('cleaned_length', 0),
                    'source': 'NCGA Evidence Content'
                }
            )
            documents.append(doc)
        
        print(f"Loaded {len(documents)} evidence documents")
        return documents
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks while preserving metadata"""
        print(f"\nChunking {len(documents)} documents...")
        
        chunks = []
        for doc in documents:
            # Split the document
            doc_chunks = self.text_splitter.split_documents([doc])
            
            # Add chunk-specific metadata
            for i, chunk in enumerate(doc_chunks):
                chunk.metadata['chunk_index'] = i
                chunk.metadata['total_chunks'] = len(doc_chunks)
                chunks.append(chunk)
        
        print(f"Created {len(chunks)} chunks")
        return chunks
    
    def create_vector_store(self, chunks: List[Document]):
        """Create or update the vector store with chunks"""
        print(f"\nCreating vector store with {len(chunks)} chunks...")
        
        # Create the vector store
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        
        # Persist the database
        vectorstore.persist()
        print(f"Vector store created and persisted to {self.persist_directory}")
        
        return vectorstore
    
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
        news_count = sum(1 for chunk in chunks if chunk.metadata['type'] == 'news')
        policy_count = sum(1 for chunk in chunks if chunk.metadata['type'] == 'policy')
        general_count = sum(1 for chunk in chunks if chunk.metadata['type'] == 'general')
        
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