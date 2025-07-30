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
from datetime import datetime

class NCGAChatbot:
    def __init__(self, api_key: str = None):
        load_dotenv()
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file")
        
        self.training_data = []
        self.load_training_data()
        
        # Define synonyms and related terms for search
        self.synonyms = {
            # Policy and Organizational Terms
            'stance': ['position', 'policy', 'view', 'opinion', 'stance', 'approach', 'perspective', 'strategy'],
            'position': ['stance', 'policy', 'view', 'opinion', 'position', 'statement', 'perspective'],
            'policy': ['stance', 'position', 'regulation', 'rule', 'guideline', 'framework', 'legislation', 'mandate'],
            
            # News and Updates
            'latest': ['recent', 'new', 'current', 'update', 'breaking', 'newest', 'today', 'recent'],
            'news': ['update', 'announcement', 'development', 'report', 'information', 'release'],
            
            # Farming and Agriculture
            'grow': ['produce', 'farm', 'cultivate', 'plant', 'raise', 'harvest', 'yield'],
            'farming': ['agriculture', 'cultivation', 'production', 'growing', 'harvesting', 'planting'],
            'farmer': ['grower', 'producer', 'agriculturalist', 'member'],
            'crop': ['corn', 'harvest', 'yield', 'produce', 'grain'],
            
            # Corn-Specific Terms
            'corn': ['maize', 'grain', 'crop', 'feedstock'],
            'yield': ['production', 'output', 'harvest', 'crop', 'return'],
            'harvest': ['yield', 'crop', 'production', 'gathering'],
            
            # Environmental and Sustainability
            'sustainable': ['environmentally friendly', 'green', 'eco-friendly', 'responsible', 'conservation'],
            'conservation': ['preservation', 'protection', 'sustainability', 'stewardship'],
            'climate': ['weather', 'environment', 'environmental', 'atmospheric'],
            
            # Energy and Biofuels
            'ethanol': ['biofuel', 'renewable fuel', 'fuel', 'bioethanol', 'corn ethanol', 'renewable'],
            'biofuel': ['ethanol', 'renewable fuel', 'alternative fuel', 'clean fuel', 'green fuel'],
            'renewable': ['sustainable', 'green', 'alternative', 'clean', 'bio-based'],
            'fuel': ['ethanol', 'biofuel', 'energy', 'power'],
            
            # Trade and Economics
            'trade': ['export', 'import', 'commerce', 'market', 'exchange', 'business'],
            'export': ['trade', 'sell', 'ship', 'market', 'international trade'],
            'import': ['trade', 'buy', 'purchase', 'international trade'],
            'market': ['trade', 'commerce', 'business', 'industry', 'sector'],
            'price': ['cost', 'value', 'rate', 'amount'],
            
            # Research and Technology
            'research': ['study', 'investigation', 'analysis', 'development', 'innovation'],
            'technology': ['tech', 'innovation', 'advancement', 'development', 'solution'],
            'innovation': ['advancement', 'development', 'improvement', 'technology'],
            
            # Government and Regulation
            'regulation': ['rule', 'law', 'requirement', 'policy', 'standard', 'mandate'],
            'standard': ['requirement', 'regulation', 'specification', 'guideline', 'criterion'],
            'compliance': ['adherence', 'conformity', 'observation', 'following'],
            
            # Carbon and Environmental Markets
            'carbon': ['emissions', 'greenhouse gas', 'ghg', 'carbon dioxide', 'co2'],
            'credit': ['offset', 'allowance', 'permit', 'certificate'],
            'emissions': ['carbon', 'pollution', 'discharge', 'output'],
            
            # Educational and Support
            'how': ['guide', 'method', 'way', 'process', 'instruction', 'procedure', 'steps'],
            'guide': ['instruction', 'direction', 'manual', 'handbook', 'resource'],
            'help': ['support', 'assistance', 'aid', 'guidance', 'resource'],
            
            # Industry and Business
            'industry': ['sector', 'business', 'market', 'field', 'commerce'],
            'commercial': ['business', 'trade', 'market', 'industry'],
            'partnership': ['collaboration', 'cooperation', 'alliance', 'relationship'],
            
            # Time and Status
            'current': ['present', 'existing', 'ongoing', 'active', 'now'],
            'future': ['upcoming', 'forthcoming', 'planned', 'projected'],
            'status': ['condition', 'state', 'situation', 'position']
        }
    
    def load_training_data(self, pages_file: str = 'ncga_cleaned_evidence_content.json', articles_file: str = 'ncga_articles.json', policy_file: str = 'ncga_policy_content.json'):
        """Load evidence-paired training data, articles, and policy documents"""
        self.training_data = []
        
        # Load pages data
        if os.path.exists(pages_file):
            with open(pages_file, 'r', encoding='utf-8') as f:
                pages_data = json.load(f)
                self.training_data.extend(pages_data)
            print(f"✅ Loaded {len(pages_data)} pages of training data")
        else:
            print(f"⚠️ {pages_file} not found")
        
        # Load articles data
        if os.path.exists(articles_file):
            with open(articles_file, 'r', encoding='utf-8') as f:
                articles_data = json.load(f)
                # Convert articles to same format as pages
                for article in articles_data:
                    self.training_data.append({
                        'title': article.get('title', ''),
                        'url': article.get('link', ''),
                        'cleaned_evidence_content': article.get('content', ''),
                        'type': 'article'
                    })
            print(f"✅ Loaded {len(articles_data)} articles")
        else:
            print(f"⚠️ {articles_file} not found")
        
        # Load policy data
        if os.path.exists(policy_file):
            with open(policy_file, 'r', encoding='utf-8') as f:
                policy_data = json.load(f)
                self.training_data.extend(policy_data)
            print(f"✅ Loaded {len(policy_data)} policy sections")
        else:
            print(f"⚠️ {policy_file} not found")
        
        print(f"📚 Total training data: {len(self.training_data)} items")
    
    def determine_query_type_weights(self, query: str) -> Dict[str, float]:
        """Use LLM to analyze query and determine optimal weights for different content types"""
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            prompt = f"""
Analyze this user query about NCGA (National Corn Growers Association) and determine how relevant each content type would be for answering it.

Content Types:
1. Policy (weight higher when query is about):
   - NCGA's official positions or stances
   - Regulations and standards
   - Long-term initiatives and programs
   - Environmental and sustainability practices, regulations, and policies
   - Industry guidelines and frameworks
   - Government relations and advocacy

2. News (weight higher ONLY when query is specifically about):
   - Recent events or developments
   - Price changes and market news
   - Breaking announcements
   - Time-sensitive information
   - Current events and immediate developments
   Note: News should NOT be weighted high for general knowledge questions or policy topics, even if news articles might contain that information

3. Main website content (weight higher when query is about):
   - Basic information and facts
   - How-to guides and educational content
   - Farming practices and techniques
   - Program details and membership info
   - Industry background and context
   - Technical explanations and definitions

4. Other (weight higher when):
   - Question is very general or casual
   - No specific NCGA content needed
   - Personal opinions or preferences
   - Non-agricultural topics

Query: {query}

Return ONLY a JSON object with these exact keys and float values 0-1 representing relevance:
{{"policy": 0.0-1.0, "news": 0.0-1.0, "general": 0.0-1.0, "other": 0.0-1.0}}

Examples:
"What's NCGA's position on carbon credits?" → {{"policy": 0.9, "news": 0.2, "general": 0.3, "other": 0.0}}
"What happened at yesterday's corn price meeting?" → {{"policy": 0.2, "news": 0.9, "general": 0.2, "other": 0.0}}
"How do I apply sustainable farming practices?" → {{"policy": 0.7, "news": 0.1, "general": 0.9, "other": 0.0}}
"When was NCGA founded?" → {{"policy": 0.0, "news": 0.0, "general": 1.0, "other": 0.1}}
"What's the weather like today?" → {{"policy": 0.0, "news": 0.0, "general": 0.0, "other": 0.9}}
"""
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful AI that analyzes queries to determine the most relevant content types for answering them. You ONLY return valid JSON objects with the exact specified format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.1
            )
            
            # Extract and parse the JSON response
            response_text = response.choices[0].message.content.strip()
            # Find the JSON object in the response (in case there's any extra text)
            json_match = re.search(r'\{.*\}', response_text)
            if json_match:
                weights = json.loads(json_match.group())
                return weights
            else:
                # Default weights if parsing fails
                return {"policy": 0.5, "news": 0.5, "general": 0.5, "other": 0.0}
                
        except Exception as e:
            print(f"Error determining query weights: {str(e)}")
            # Return default weights on error
            return {"policy": 0.5, "news": 0.5, "general": 0.5, "other": 0.0}

    def search_relevant_content(self, query: str, top_k: int = 1) -> List[Dict]:
        """Search for relevant content based on user query"""
        relevant_content = []
        
        # Get dynamic weights for different content types
        weights = self.determine_query_type_weights(query)
        
        # If query is determined to be general/other with high confidence, return empty
        if weights['other'] > 0.8:
            return []
        
        # Simple keyword matching with synonym handling
        query_lower = query.lower()
        
        # Extract key terms from query (excluding stop words)
        stop_words = {'what', 'is', 'are', 'the', 'and', 'for', 'with', 'about', 'from', 'this', 'that', 'they', 'have', 'been', 'will', 'would', 'could', 'should', 'tell', 'me', 'do', 'does', 'can', 'you', 'your', 'we', 'our', 'their', 'my', 'to', 'of', 'in', 'on', 'at', 'by'}
        query_terms = [word for word in query_lower.split() if word not in stop_words]
        
        # Create bigrams from query terms
        query_bigrams = []
        for i in range(len(query_terms) - 1):
            query_bigrams.append(f"{query_terms[i]} {query_terms[i + 1]}")
        
        # Expand query terms with synonyms
        expanded_terms = set()
        primary_terms = set()  # Track original query terms for boosting
        for term in query_terms:
            expanded_terms.add(term)
            primary_terms.add(term)
            for key, values in self.synonyms.items():
                if term in values or term == key:
                    expanded_terms.update(values)
        
        for page in self.training_data:
            content = page.get('cleaned_evidence_content', '').lower()
            title = page.get('title', '').lower()
            page_type = page.get('type', 'page')
            
            # Initialize scoring components
            exact_match_score = 0
            term_match_score = 0
            bigram_match_score = 0
            title_match_score = 0
            primary_term_bonus = 0
            
            # Check for exact phrase matches
            if query_lower in content:
                exact_match_score = 10.0
            if query_lower in title:
                exact_match_score = 15.0  # Higher score for title exact match
            
            # Check for bigram matches
            for bigram in query_bigrams:
                if bigram in content:
                    bigram_match_score += 3.0
                if bigram in title:
                    bigram_match_score += 4.0
            
            # Check for individual term matches including synonyms
            content_terms = set(content.split())
            title_terms = set(title.split())
            
            # Score primary (original query) terms higher
            for term in primary_terms:
                if term in content_terms:
                    primary_term_bonus += 2.0
                if term in title_terms:
                    primary_term_bonus += 3.0
            
            # Score expanded terms
            for term in expanded_terms:
                if term in content:
                    term_match_score += 1.0
                if term in title:
                    title_match_score += 2.0
            
            # Calculate total base score
            base_score = (
                exact_match_score +
                bigram_match_score +
                term_match_score +
                title_match_score +
                primary_term_bonus
            )
            
            if base_score > 0:
                # Apply content type weights
                if page_type == 'policy':
                    final_score = base_score * (1 + weights['policy'] * 2)
                elif page_type == 'article':
                    final_score = base_score * (1 + weights['news'] * 2)
                else:
                    final_score = base_score * (1 + weights['general'] * 2)
                
                # Boost score for highly relevant content types
                content_type_bonus = 0
                if page_type == 'policy' and weights['policy'] > 0.7:
                    content_type_bonus = 5.0
                elif page_type == 'article' and weights['news'] > 0.7:
                    content_type_bonus = 5.0
                elif page_type == 'page' and weights['general'] > 0.7:
                    content_type_bonus = 5.0
                
                # Additional boost for title relevance to query topic
                topic_terms = set(expanded_terms)
                title_terms = set(title.split())
                title_relevance = len(topic_terms.intersection(title_terms))
                if title_relevance > 0:
                    content_type_bonus += title_relevance * 2
                
                final_score += content_type_bonus
                
                relevant_content.append({
                    'title': page.get('title', ''),
                    'url': page.get('url', ''),
                    'content': page.get('cleaned_evidence_content', ''),
                    'type': page_type,
                    'relevance_score': final_score,
                    'match_details': {
                        'exact_match': exact_match_score > 0,
                        'bigram_matches': bigram_match_score > 0,
                        'term_matches': term_match_score,
                        'title_matches': title_match_score,
                        'primary_term_bonus': primary_term_bonus,
                        'content_type_bonus': content_type_bonus
                    }
                })
        
        # Sort by relevance and return top results
        relevant_content.sort(key=lambda x: x['relevance_score'], reverse=True)
        return relevant_content[:top_k]
    
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
    
    def generate_response(self, query: str, relevant_content: List[Dict]) -> str:
        """Generate a response using OpenAI's API"""
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            context = self.format_context(relevant_content)
            
            # Get current date in YYYY-MM format
            current_date = datetime.now().strftime("%Y-%m")
            
            prompt = f"""
You are a helpful AI assistant trained on NCGA (National Corn Growers Association) information. 

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
6. Focus on answering the user's specific question directly
7. Look for specific topic information in the evidence
8. Citation rules:
   - When you use information from a source, ALWAYS cite it with the exact URL from the context
   - Never cite or mention sources that don't contain relevant information
   - Format citations as: Source: (exact_url)
   - If evidence exists but isn't relevant to the question, ignore it completely
9. Be direct and helpful
10. When no relevant information is found:
    - Simply state that you don't have the requested information
    - DO NOT mention or cite any sources
    - DO NOT explain what content you looked at
    - Suggest where the user might find the information (e.g., "You can find current corn prices on...")
    - Keep the response brief and direct

Examples of good responses:

With relevant info:
"Ethanol production creates a significant market for corn farmers, using approximately 30% of U.S. field corn annually. This helps stabilize corn prices and provides a reliable market for farmers. Source: (https://ncga.com/key-issues/current-priorities/ethanol)"

With no relevant info:
"I don't have current information about corn prices. You can find up-to-date pricing data on commodity trading websites or through your local grain elevator."

Examples of BAD responses:
❌ "The provided article from 2022 doesn't contain information about corn prices..."
❌ "While the source discusses ethanol production, it doesn't mention board members..."
❌ "Here's a link to an article that doesn't answer your question..."
❌ "The source/article mentions [irrelevant information] but doesn't address your specific question..."

User Question: {query}

Current Date: {current_date}

{context}

Please provide a helpful, accurate response based on the evidence above. Remember:
1. Only cite sources that directly answer the question with relevant information
2. When citing, ALWAYS use the exact URL in parentheses: Source: (url)
3. Never mention or link to content that doesn't help answer the question
4. Keep "no information" responses brief and direct
5. Write as if speaking directly to the user
6. Be clear about temporal context when information is found
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