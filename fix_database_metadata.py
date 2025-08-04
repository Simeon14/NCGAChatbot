#!/usr/bin/env python3
"""
Fix ChromaDB metadata labeling issue
All documents are currently labeled as 'news' but should be properly categorized as:
- 'news' for news articles (URLs containing '/article/')
- 'policy' for policy documents 
- 'general' for other NCGA content
"""

import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv

def fix_metadata_labels():
    """Fix the metadata labels in the ChromaDB collection"""
    load_dotenv()
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path="chroma_db_metadata")
    collections = client.list_collections()
    
    if not collections:
        print("❌ No collections found!")
        return
    
    # Use the existing collection
    collection = collections[0]
    print(f"📦 Working with collection: {collection.name}")
    
    # Get all documents in batches
    total_docs = collection.count()
    print(f"📊 Total documents to process: {total_docs}")
    
    batch_size = 1000
    fixed_count = 0
    
    for offset in range(0, total_docs, batch_size):
        print(f"🔄 Processing batch {offset//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}")
        
        # Get batch of documents
        results = collection.get(
            limit=batch_size,
            offset=offset,
            include=['documents', 'metadatas']
        )
        
        # Process each document in the batch
        for doc_id, metadata in zip(results['ids'], results['metadatas']):
            if not metadata:
                continue
                
            url = metadata.get('url', '')
            original_type = metadata.get('type', 'unknown')
            
            # Determine correct type based on URL and content
            new_type = determine_content_type(url, metadata)
            
            # Update if type changed
            if new_type != original_type:
                try:
                    # Update the metadata
                    updated_metadata = metadata.copy()
                    updated_metadata['type'] = new_type
                    
                    collection.update(
                        ids=[doc_id],
                        metadatas=[updated_metadata]
                    )
                    fixed_count += 1
                    
                    if fixed_count % 100 == 0:
                        print(f"  ✅ Fixed {fixed_count} documents so far...")
                        
                except Exception as e:
                    print(f"  ❌ Error updating {doc_id}: {e}")
    
    print(f"\n🎉 Fixed metadata for {fixed_count} documents!")
    
    # Verify the fix
    verify_fix(collection)

def determine_content_type(url, metadata):
    """Determine the correct content type based on URL and metadata"""
    url_lower = url.lower()
    title = metadata.get('title', '').lower()
    
    # News articles - URLs containing '/article/' or news-related paths
    if ('/article/' in url_lower or 
        '/news/' in url_lower or 
        '/media/' in url_lower or
        'stay-informed' in url_lower):
        return 'news'
    
    # Policy documents - URLs containing policy-related terms
    elif (any(term in url_lower for term in ['policy', 'position', 'statement', 'advocacy', 'legislation']) or
          any(term in title for term in ['policy', 'position', 'statement', 'advocacy', 'legislation'])):
        return 'policy'
    
    # General content - everything else
    else:
        return 'general'

def verify_fix(collection):
    """Verify that the fix worked by showing type distribution"""
    print("\n🔍 Verifying fix - checking content type distribution:")
    
    # Sample documents to check types
    sample_size = min(1000, collection.count())
    results = collection.get(
        limit=sample_size,
        include=['metadatas']
    )
    
    type_counts = {}
    for metadata in results['metadatas']:
        content_type = metadata.get('type', 'unknown')
        type_counts[content_type] = type_counts.get(content_type, 0) + 1
    
    for content_type, count in type_counts.items():
        percentage = (count / sample_size) * 100
        print(f"  {content_type}: {count} documents ({percentage:.1f}%)")

if __name__ == "__main__":
    print("🔧 Starting ChromaDB metadata fix...")
    fix_metadata_labels()
    print("✅ Metadata fix complete!")