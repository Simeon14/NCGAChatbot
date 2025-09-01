import streamlit as st
import os
import time
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
        api_key = st.secrets.get("OPENAI_API_KEY")
    except:
        api_key = None
    
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
                search_query = st.session_state.chatbot.enhance_query_with_context(prompt, st.session_state.messages)
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
                
                # Auto-save every interaction to feedback system
                try:
                    from feedback_system import FeedbackSystem
                    fs = FeedbackSystem()
                    fs.save_interaction(
                        user_query=prompt,
                        chatbot_response=response,
                        session_id=session_id,
                        response_time_ms=response_time_ms,
                        sources_used=sources_used,
                        model_used=model_used
                    )
                except Exception as save_error:
                    print(f"❌ Error auto-saving interaction: {save_error}")
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
                # Auto-save error interactions too
                try:
                    from feedback_system import FeedbackSystem
                    fs = FeedbackSystem()
                    fs.save_interaction(
                        user_query=prompt,
                        chatbot_response=error_msg,
                        session_id=str(hash(st.session_state.get('_session_id', time.time()))),
                        model_used="gpt-4o"
                    )
                except Exception as save_error:
                    print(f"❌ Error auto-saving error interaction: {save_error}")

# Global feedback buttons in sidebar (outside chat context)
if 'last_response' in st.session_state and 'last_query' in st.session_state:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Rate the last response:**")
    
    if st.sidebar.button("👍 Like Last Response", key="like_last"):
        from feedback_system import FeedbackSystem
        fs = FeedbackSystem()
        success = fs.update_rating(st.session_state.last_query, st.session_state.last_response, 1)
        if success:
            st.sidebar.success("👍 Rating updated!")
        else:
            st.sidebar.error("❌ Could not update rating")
    
    if st.sidebar.button("👎 Dislike Last Response", key="dislike_last"):
        from feedback_system import FeedbackSystem
        fs = FeedbackSystem()
        success = fs.update_rating(st.session_state.last_query, st.session_state.last_response, 0)
        if success:
            st.sidebar.success("👎 Rating updated!")
        else:
            st.sidebar.error("❌ Could not update rating")
