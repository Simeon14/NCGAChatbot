import streamlit as st
import os
import time
import openai
import json
from ncga_chatbot import NCGAChatbot
from feedback_system import render_feedback_buttons, render_feedback_dashboard

# Page configuration
st.set_page_config(
    page_title="NCGA Chatbot",
    page_icon="🌽",
    layout="wide"
)

# Initialize session state for feedback
if 'show_feedback_form' not in st.session_state:
    st.session_state.show_feedback_form = False

# Title and description
st.title("🌽 NCGA Chatbot")
st.markdown("Ask me about corn farming, sustainability, trade policy, or other NCGA topics!")

# Sidebar for API key
with st.sidebar:
    st.header("🔑 Setup")
    st.markdown("Enter your OpenAI API key to get started.")
    
    # Initialize session state for API key
    if 'api_key_input' not in st.session_state:
        st.session_state.api_key_input = ""
    if 'show_api_input' not in st.session_state:
        st.session_state.show_api_input = False
    
    # Get API key from secrets or user input
    try:
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except:
        api_key = os.getenv("OPENAI_API_KEY")
    
    # Show API key input or success message
    if not api_key or st.session_state.show_api_input:
        api_key = st.text_input("OpenAI API Key:", type="password", help="Get your API key from https://platform.openai.com/api-keys", value=st.session_state.api_key_input, key="api_key_input")
    else:
        st.success("✅ API key configured!")
        if st.button("🔄 Reset API Key"):
            # Clear the API key and session state
            st.session_state.api_key_input = ""
            st.session_state.show_api_input = True
            # Clear other session state
            for key in list(st.session_state.keys()):
                if key not in ['api_key_input', 'show_api_input']:
                    del st.session_state[key]
            st.rerun()
    
    if not api_key:
        st.warning("⚠️ Please enter your OpenAI API key to continue")
        st.stop()
    
    # About section
    st.header("ℹ️ About")
    st.markdown("""
    This chatbot is trained on NCGA (National Corn Growers Association) information.
    """)

# Initialize chatbot
if 'chatbot' not in st.session_state:
    with st.spinner("Loading NCGA data..."):
        st.session_state.chatbot = NCGAChatbot(api_key=api_key)
    st.success("✅ Chatbot ready!")

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Clear chat button
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.messages = []  # Clear chat history
    st.rerun()

# Chat input
if prompt := st.chat_input("Ask me about NCGA topics..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response with timing
    with st.chat_message("assistant"):
        with st.spinner("🤔 Searching for information..."):
            try:
                start_time = time.time()
                
                # Handle follow-up questions by combining with previous context
                search_query = prompt
                if len(st.session_state.messages) >= 2:
                    # Use LLM to determine if this is a follow-up question and get the original topic
                    try:
                        client = openai.OpenAI(api_key=api_key)
                        
                        # Format full conversation history for context
                        full_history = ""
                        for msg in st.session_state.messages:
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

Current user query: "{prompt}"

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
                            search_query = f"{analysis['original_topic']} {prompt}"
                            
                    except Exception as e:
                        # Fallback to simple pattern matching if LLM analysis fails
                        current_query_words = len(prompt.split())
                        is_likely_followup = (
                            current_query_words <= 3 or 
                            any(pattern in prompt.lower() for pattern in ['more', 'else', 'again', 'continue', 'go on', 'and?', 'what about', 'how about'])
                        )
                        
                        if is_likely_followup:
                            # Find the most recent substantial user question
                            last_substantial_question = None
                            for msg in reversed(st.session_state.messages):
                                if msg["role"] == "user":
                                    msg_words = len(msg["content"].split())
                                    is_short = msg_words <= 3
                                    is_followup = any(pattern in msg["content"].lower() for pattern in ['more', 'else', 'again', 'continue', 'go on', 'and?', 'what about', 'how about'])
                                    
                                    if not is_short and not is_followup:
                                        last_substantial_question = msg["content"]
                                        break
                            
                            if last_substantial_question:
                                search_query = f"{last_substantial_question} {prompt}"
                
                relevant = st.session_state.chatbot.search_relevant_content(search_query)
                
                if relevant:
                    with st.spinner("📚 Thinking..."):
                        response = st.session_state.chatbot.generate_response(
                            prompt, 
                            relevant,
                            st.session_state.messages[:-1]  # Pass all previous messages except current query
                        )
                else:
                    response = "I don't have specific information about that topic in my NCGA training data. Please try asking about corn farming, sustainability, trade policy, or other NCGA-related topics."
                
                end_time = time.time()
                response_time_ms = int((end_time - start_time) * 1000)
                
                st.markdown(response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Store last query and response for feedback
                st.session_state.last_query = prompt
                st.session_state.last_response = response
                
                # Get session ID for tracking
                session_id = str(hash(st.session_state.get('_session_id', time.time())))
                
                # Extract sources used (if available)
                sources_used = []
                if relevant:
                    for item in relevant:
                        sources_used.append({
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'type': item.get('type', 'page')
                        })
                
                # Get model used
                model_used = "gpt-4o"  # Update this if you change models
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Global feedback buttons in sidebar (outside chat context)
if 'last_response' in st.session_state and 'last_query' in st.session_state:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Feedback:**")
    
    if st.sidebar.button("👍 Like Last Response", key="like_last"):
        print("DEBUG: Like last response clicked!")
        from feedback_system import FeedbackSystem
        fs = FeedbackSystem()
        success = fs.save_feedback(st.session_state.last_query, st.session_state.last_response, 1)
        print(f"DEBUG: Like save result: {success}")
        st.sidebar.success("Like saved!")
    
    if st.sidebar.button("👎 Dislike Last Response", key="dislike_last"):
        print("DEBUG: Dislike last response clicked!")
        from feedback_system import FeedbackSystem
        fs = FeedbackSystem()
        success = fs.save_feedback(st.session_state.last_query, st.session_state.last_response, 0)
        print(f"DEBUG: Dislike save result: {success}")
        st.sidebar.success("Dislike saved!")
