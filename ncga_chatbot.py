#!/usr/bin/env python3
"""
NCGA Chatbot
A RAG chatbot that uses evidence-paired training data to provide accurate responses.
"""

# Fix SQLite version issue by using pysqlite3-binary
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
import openai
from dotenv import load_dotenv
from typing import List, Dict, Any
import re
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions

class NCGAChatbot:
    def __init__(self, api_key: str = None):
        load_dotenv()
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file")
                
        # Initialize ChromaDB directly (no LangChain wrapper needed)
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.api_key,
            model_name="text-embedding-ada-002"
        )
        
        # Create/load ChromaDB collection with persistent storage (SQLite fixed)
        self.chroma_client = chromadb.PersistentClient(path="chroma_db_metadata")
        
        # Use the existing collection (could be "langchain" or "ncga_documents")
        collections = self.chroma_client.list_collections()
        if collections:
            # Use the existing collection (backwards compatibility)
            existing_collection = collections[0]
            self.collection = self.chroma_client.get_collection(
                name=existing_collection.name,
                embedding_function=self.openai_ef
            )
        else:
            # Create new collection if none exist
            self.collection = self.chroma_client.get_or_create_collection(
                name="ncga_documents",
                embedding_function=self.openai_ef
            )
        
        # Check collection size
        count = self.collection.count()
        print(f"📊 Loaded {count} NCGA documents")
    
    def search_relevant_content(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Perform semantic search using ChromaDB directly (no LangChain needed)
        For temporal queries, prioritize recent content by date
        """
        try:
            # Check if this is a temporal query that needs date-aware search
            temporal_keywords = ['recent', 'latest', 'current', 'new', 'newest', 'today', 'this week', 'this month']
            is_temporal_query = any(keyword in query.lower() for keyword in temporal_keywords)
            
            # For temporal queries, get more results to ensure we have recent content
            search_limit = 50 if is_temporal_query else top_k
            
            # Query ChromaDB collection directly
            results = self.collection.query(
                query_texts=[query],
                n_results=search_limit,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results to match expected structure
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for doc, metadata, distance in zip(
                    results['documents'][0], 
                    results['metadatas'][0], 
                    results['distances'][0]
                ):
                    result = {
                        'content': doc,
                        'score': 1.0 - distance,  # Convert distance to similarity
                        'type': metadata.get('type', 'general'),
                        'url': metadata.get('url', ''),
                        'title': metadata.get('title', 'Untitled'),
                        'pub_date': metadata.get('pub_date', '')
                    }
                    
                    formatted_results.append(result)
            
            # For temporal queries, sort by date (newest first) and limit results
            if is_temporal_query and formatted_results:
                from datetime import datetime
                
                def parse_date(date_str):
                    try:
                        # Parse the date format: "Thu, 24 Jul 2025 09:25:24 -0500"
                        return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                    except:
                        return datetime.min  # Put unparseable dates at the end
                
                # Sort by date (newest first)
                formatted_results.sort(key=lambda x: parse_date(x.get('pub_date', '')), reverse=True)
                
                # Limit to top_k results after sorting
                formatted_results = formatted_results[:top_k]
                
                print(f"🔍 Temporal query detected, sorted {len(formatted_results)} results by date")
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ ChromaDB search error: {e}")
            return []
    
    def determine_query_category(self, query: str) -> str:
        """
        Determine if the query is about news or policy/general content.
        Returns either 'news' or 'policy_general'
        """
        # Simple keyword-based classification (no LangChain needed)
        query_lower = query.lower()
        news_keywords = ['news', 'recent', 'latest', 'current', 'today', 'yesterday', 'article', 'update']
        
        # Check if query contains news-related keywords
        if any(keyword in query_lower for keyword in news_keywords):
            return 'news'
        else:
            return 'policy_general'

    def format_context(self, relevant_content: List[Dict]) -> str:
        """Format relevant content for the AI prompt"""
        context = "Based on the following NCGA (National Corn Growers Association) information:\n\n"
        
        for item in relevant_content:
            item_type = item.get('type', 'page')
            # Extract date from URL if it's an article
            date_str = ""
            if item_type == 'article' and '/article/' in item.get('url', ''):
                try:
                    date_match = re.search(r'/article/(\d{4})/(\d{2})/', item.get('url', ''))
                    if date_match:
                        year = date_match.group(1)
                        month = date_match.group(2)
                        date_str = f" (Published: {year}-{month})"
                except:
                    pass
            
            if item_type == 'article':
                context += f"ARTICLE{date_str}:\n"
            elif item_type == 'policy':
                context += f"POLICY DOCUMENT:\n"
            else:
                context += f"PAGE:\n"
            context += f"URL: {item['url']}\n"
            context += f"CONTENT:\n{item['content']}\n\n"
        
        return context
    
    def generate_response(self, query: str, relevant_content: List[Dict], chat_history: List[Dict] = None) -> str:
        """Generate a response using OpenAI's API"""
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            context = self.format_context(relevant_content)
            
            # Format chat history if provided
            history_context = ""
            if chat_history:
                history_context = "\nPrevious conversation:\n"
                for msg in chat_history:
                    if msg["role"] == "user":
                        history_context += f"User: {msg['content']}\n"
                    else:
                        history_context += f"Assistant: {msg['content']}\n"
            
            # Get current date in YYYY-MM format
            current_date = datetime.now().strftime("%Y-%m")
            
            prompt = f"""
You are a helpful AI assistant trained on NCGA (National Corn Growers Association) information. 

Current Date: {current_date}

Previous Conversation:
{history_context if chat_history else "No previous conversation."}

User Question: {query}

{context}

IMPORTANT RULES:
1. Only provide information that is explicitly stated in the evidence provided
2. Write responses directly to the user - never reference sources as if they are the ones providing the information
3. If you're not sure about something, say so rather than guessing
4. Be accurate and factual
5. CRITICAL: Always check the date of the information
   - For news articles, explicitly state when the information was published
   - If information is more than 1 year old, add a clear disclaimer about its age
   - For market data or time-sensitive information, emphasize that it represents a specific point in time
   - If asked about current trends/prices/status, emphasize that more recent information may be available

5a. TEMPORAL AWARENESS FOR NEWS QUERIES:
   - When asked for "recent", "latest", "current", or "new" news, ALWAYS prioritize the most recent dates available
   - NEVER call older information "recent" if newer information exists in the evidence
   - Compare ALL article dates in the evidence and identify the truly most recent content
   - If asked for recent news, start your response with the newest articles first
   - Example: If you have articles from 2023 and 2025, the 2025 articles are "recent", not the 2023 ones
6. Focus on answering the user's specific question directly
7. Look for specific topic information in the evidence
8. Citation rules:
   - When you use information from ANY source (web URL, PDF, or document), ALWAYS cite it
   - Use the exact URL/reference from the context, whether it's a web link or PDF filename
   - Never cite or mention sources that don't contain relevant information
   - Format citations as: Source: (exact_url_or_document_reference)
   - For policy documents with PDF references, still cite them: Source: (Policy and Position Papers v. 7.16.25 FINAL.pdf)
   - If evidence exists but isn't relevant to the question, ignore it completely
9. Be direct and helpful
10. When no relevant information is found:
    - Simply state that you don't have the requested information
    - DO NOT mention or cite any sources
    - DO NOT explain what content you looked at
    - Suggest where the user might find the information (e.g., "You can find current corn prices on...")
    - Keep the response brief and direct
11. Use conversation context:
    - Consider previous questions and answers when responding
    - If the user refers to previous information, acknowledge it
    - Maintain consistency with previous responses
    - If clarifying or updating previous information, explain why

Examples of good responses:

With relevant info from web article:
"Ethanol production creates a significant market for corn farmers, using approximately 30% of U.S. field corn annually. This helps stabilize corn prices and provides a reliable market for farmers. Source: (https://ncga.com/key-issues/current-priorities/ethanol)"

With relevant info from policy document:
"The NCGA supports revenue-based risk management tools with proportional federal cost sharing for price and yield risks. They also advocate for increased funding for the Market Access Program to promote U.S. corn and corn products. Source: (Policy and Position Papers v. 7.16.25 FINAL.pdf)"

With no relevant info:
"I don't have current information about corn prices. You can find up-to-date pricing data on commodity trading websites or through your local grain elevator."

Examples of BAD responses:
❌ "The provided article from 2022 doesn't contain information about corn prices..."
❌ "While the source discusses ethanol production, it doesn't mention board members..."
❌ "Here's a link to an article that doesn't answer your question..."
❌ "The source/article mentions [irrelevant information] but doesn't address your specific question..."
❌ "The most recent news is from July 2023..." (when 2025 articles exist in the evidence)
❌ Calling 2023 content "recent" when 2024 or 2025 content is available

Please provide a helpful, accurate response based on the evidence above. Remember:
1. Only cite sources that directly answer the question with relevant information
2. When citing, ALWAYS use the exact URL or document reference in parentheses: Source: (url_or_document_name)
3. ALWAYS cite policy documents even if they reference PDF files: Source: (Policy and Position Papers v. 7.16.25 FINAL.pdf)
4. Never mention or link to content that doesn't help answer the question
5. Keep "no information" responses brief and direct
6. Write as if speaking directly to the user
7. Be clear about temporal context when information is found
8. Consider the conversation history when responding
9. FOR TEMPORAL QUERIES: Always check ALL article dates and prioritize the most recent content first
"""
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that provides accurate information based on evidence. Always cite sources using just the URL in parentheses (url), be direct in your responses, and be clear about when information was published."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def enhance_query_with_context(self, user_input: str, chat_history: List[Dict] = None) -> str:
        """Enhance user query with conversation context for follow-up questions"""
        search_query = user_input
        
        if chat_history and len(chat_history) >= 2:
            # Use LLM to determine if this is a follow-up question and get the original topic
            try:
                client = openai.OpenAI(api_key=self.api_key)
                
                # Format full conversation history for context
                full_history = ""
                for msg in chat_history:
                    if msg["role"] == "user":
                        full_history += f"User: {msg['content']}\n"
                    else:
                        full_history += f"Assistant: {msg['content']}\n"
                
                followup_analysis = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are analyzing whether a user's current query is a follow-up question that refers to a previous topic in the conversation. Follow-up questions include: asking for more information, additional details, other aspects, different points, or anything else about the same topic. You must respond with valid JSON only, no other text."},
                        {"role": "user", "content": f"""Analyze this conversation and the current user query:

Full conversation:
{full_history}

Current user query: "{user_input}"

Determine:
1. Is this a follow-up question that refers to a previous topic? Consider phrases like "another thing", "what else", "anything else", "more", "additional", "other", etc. as follow-ups, as well as prompts that don't seem to be about a new topic (true/false)
2. If yes, what was the original topic/question that this follows up on? (extract ONLY the exact key topic the user mentioned, do not add additional context or expand it)

Respond with valid JSON only:
{{
    "is_followup": true/false,
    "original_topic": "key topic or null"
}}"""}
                    ],
                    max_tokens=150,
                    temperature=0.1
                )
                
                response_text = followup_analysis.choices[0].message.content.strip()
                
                # Try to extract JSON from the response
                try:
                    analysis = json.loads(response_text)
                except json.JSONDecodeError:
                    # Try to find JSON in the response
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
                    else:
                        raise Exception("No valid JSON found in response")
                
                if analysis.get("is_followup") and analysis.get("original_topic"):
                    # Combine the follow-up with the original topic
                    search_query = f"{analysis['original_topic']} {user_input}"
                    
            except Exception as e:
                # Fallback to simple pattern matching if LLM analysis fails
                current_query_words = len(user_input.split())
                is_likely_followup = (
                    current_query_words <= 3 or 
                    any(pattern in user_input.lower() for pattern in ['more', 'else', 'again', 'continue', 'go on', 'and?', 'what about', 'how about'])
                )
                
                if is_likely_followup:
                    # Find the most recent substantial user question
                    last_substantial_question = None
                    for msg in reversed(chat_history):
                        if msg["role"] == "user":
                            msg_words = len(msg["content"].split())
                            is_short = msg_words <= 3
                            is_followup = any(pattern in msg["content"].lower() for pattern in ['more', 'else', 'again', 'continue', 'go on', 'and?', 'what about', 'how about'])
                            
                            if not is_short and not is_followup:
                                last_substantial_question = msg["content"]
                                break
                    
                    if last_substantial_question:
                        search_query = f"{last_substantial_question} {user_input}"
        
        return search_query
    
    def chat(self):
        """Interactive chat interface"""
        print("🌽 NCGA Chatbot")
        print("=" * 50)
        print("Ask me about corn farming, ethanol, trade policy, or other NCGA topics!")
        print("Type 'quit' to exit\n")
        
        chat_history = []
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Thanks for chatting! 👋")
                    break
                
                if not user_input:
                    continue
                
                print("🤔 Searching for relevant information...")
                
                # Handle follow-up questions by combining with previous context
                search_query = self.enhance_query_with_context(user_input, chat_history)
                
                relevant_content = self.search_relevant_content(search_query)
                
                if relevant_content:
                    print("📚 Found relevant information, generating response...")
                    response = self.generate_response(user_input, relevant_content, chat_history)
                    print(f"\nBot: {response}\n")
                    chat_history.append({"role": "user", "content": user_input})
                    chat_history.append({"role": "assistant", "content": response})
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