import streamlit as st
import os
from ncga_chatbot import NCGAChatbot

# Page configuration
st.set_page_config(
    page_title="NCGA Chatbot",
    page_icon="🌽",
    layout="wide"
)

# Title and description
st.title("🌽 NCGA Chatbot")
st.markdown("Ask me about corn farming, sustainability, trade policy, or other NCGA topics!")

# Sidebar for API key
with st.sidebar:
    st.header("🔑 Setup")
    st.markdown("Enter your OpenAI API key to get started.")
    
    # Get API key from secrets or user input
    try:
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        api_key = st.text_input("OpenAI API Key:", type="password", help="Get your API key from https://platform.openai.com/api-keys")
    
    if not api_key:
        st.warning("⚠️ Please enter your OpenAI API key to continue")
        st.stop()
    
    st.success("✅ API key configured!")
    
    # Add Reset API Key button
    if st.button("🔄 Reset API Key"):
        # Clear the session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
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
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Searching for information..."):
            try:
                relevant = st.session_state.chatbot.search_relevant_content(prompt)
                
                if relevant:
                    with st.spinner("📚 Thinking..."):
                        response = st.session_state.chatbot.generate_response(
                            prompt, 
                            relevant,
                            st.session_state.messages[:-1]  # Pass all previous messages except current query
                        )
                else:
                    response = "I don't have specific information about that topic in my NCGA training data. Please try asking about corn farming, sustainability, trade policy, or other NCGA-related topics."
                
                st.markdown(response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Built with Streamlit and OpenAI") # Test comment
