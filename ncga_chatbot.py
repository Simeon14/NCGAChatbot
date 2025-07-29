#!/usr/bin/env python3
"""
NCGA Chatbot
A simple RAG chatbot that uses evidence-paired training data to provide accurate responses.
"""

import json
import os
import openai
from dotenv import load_dotenv
from typing import List, Dict, Any
import re

class NCGAChatbot:
    def __init__(self, api_key: str = None):
        load_dotenv()
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file")
        
        self.training_data = []
        self.load_training_data()
    
    def load_training_data(self, data_file: str = 'ncga_cleaned_evidence_content.json'):
        """Load the evidence-paired training data"""
        if not os.path.exists(data_file):
            print(f"❌ {data_file} not found")
            return
        
        with open(data_file, 'r', encoding='utf-8') as f:
            self.training_data = json.load(f)
        
        print(f"✅ Loaded {len(self.training_data)} pages of training data")
    
    def search_relevant_content(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for relevant content based on user query"""
        relevant_content = []
        
        # Simple keyword matching (you could use more sophisticated search)
        query_lower = query.lower()
        query_words = query_lower.split()
        
        for page in self.training_data:
            content = page.get('cleaned_evidence_content', '')
            title = page.get('title', '')
            
            # Check if query matches page content
            content_lower = content.lower()
            title_lower = title.lower()
            
            # Check for exact phrase match first
            if query_lower in content_lower or query_lower in title_lower:
                relevant_content.append({
                    'title': title,
                    'url': page.get('url', ''),
                    'content': content,
                    'relevance_score': 2.0
                })
            else:
                # Check for individual word matches
                word_matches = 0
                for word in query_words:
                    if len(word) > 2:  # Only count words longer than 2 characters
                        if word in content_lower or word in title_lower:
                            word_matches += 1
                
                if word_matches > 0:
                    relevant_content.append({
                        'title': title,
                        'url': page.get('url', ''),
                        'content': content,
                        'relevance_score': word_matches
                    })
        
        # Sort by relevance and return top results
        relevant_content.sort(key=lambda x: x['relevance_score'], reverse=True)
        return relevant_content[:top_k]
    
    def format_context(self, relevant_content: List[Dict]) -> str:
        """Format relevant content for the AI prompt"""
        context = "Based on the following NCGA (National Corn Growers Association) information:\n\n"
        
        for item in relevant_content:
            context += f"PAGE: {item['title']}\n"
            context += f"URL: {item['url']}\n"
            context += f"CONTENT:\n{item['content']}\n\n"
        
        return context
    
    def generate_response(self, query: str, relevant_content: List[Dict]) -> str:
        """Generate a response using OpenAI's API"""
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            context = self.format_context(relevant_content)
            
            prompt = f"""
You are a helpful AI assistant trained on NCGA (National Corn Growers Association) information. 

IMPORTANT RULES:
1. Only provide information that is explicitly stated in the evidence provided
2. Always cite your sources when making claims - use the exact URLs provided in the context
3. If you're not sure about something, say so rather than guessing
4. Be accurate and factual
5. If the evidence shows time-sensitive information, mention that it may need verification
6. Focus on answering the user's specific question directly
7. Look for specific topic information in the evidence - if the user asks about "trade policy" and you find trade-related content, use it
8. If you find evidence that answers the user's question, present it clearly and cite the source
9. Be direct and helpful - if the evidence contains relevant information, share it
10. ONLY say "not explicitly mentioned" if you truly find NO relevant evidence - if you cite a source, you must have found relevant information

User Question: {query}

{context}

Please provide a helpful, accurate response based on the evidence above. If you make any claims, cite the specific evidence that supports them using the exact URLs provided. If you find relevant information in the evidence, present it clearly. Only say information is "not explicitly mentioned" if you truly find no relevant evidence.
"""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that provides accurate information based on evidence. Always cite your sources and be direct in your responses. If you find relevant evidence, present it clearly."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def chat(self):
        """Interactive chat interface"""
        print("🌽 NCGA Chatbot")
        print("=" * 50)
        print("Ask me about corn farming, ethanol, trade policy, or other NCGA topics!")
        print("Type 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Thanks for chatting! 👋")
                    break
                
                if not user_input:
                    continue
                
                print("🤔 Searching for relevant information...")
                relevant_content = self.search_relevant_content(user_input)
                
                if relevant_content:
                    print("📚 Found relevant information, generating response...")
                    response = self.generate_response(user_input, relevant_content)
                    print(f"\nBot: {response}\n")
                else:
                    print("\nBot: I don't have specific information about that topic in my NCGA training data. Please try asking about corn farming, ethanol, trade policy, or other NCGA-related topics.\n")
                    
            except KeyboardInterrupt:
                print("\n\nThanks for chatting! 👋")
                break
            except Exception as e:
                print(f"\nBot: Sorry, I encountered an error: {e}\n")

def main():
    """Main function"""
    try:
        chatbot = NCGAChatbot()
        chatbot.chat()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 