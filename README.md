# 🌽 NCGA Chatbot

A web-based chatbot trained on National Corn Growers Association (NCGA) information that provides evidence-backed responses about corn farming, ethanol, trade policy, and other NCGA topics.

## Features

- **Evidence-backed responses** - All information is sourced from NCGA content
- **Web interface** - Easy to use on any device
- **Secure API handling** - Users provide their own OpenAI API keys
- **Comprehensive knowledge** - Trained on 724 items (20 main pages + 704 articles)

## Topics Covered

- Corn farming practices
- Ethanol production and policy
- Trade policy and market development
- Federal tax policy for farmers
- Farm bill priorities
- Animal agriculture
- Carbon markets and sustainability
- And more!

## How to Use

1. Visit the deployed app URL
2. Enter your OpenAI API key in the sidebar
3. Start asking questions about NCGA topics!

## Technical Details

- Built with Streamlit
- Uses OpenAI GPT-3.5-turbo for response generation
- RAG (Retrieval-Augmented Generation) architecture
- Evidence matching to prevent hallucinations

## Files

- `app.py` - Streamlit web application
- `ncga_chatbot.py` - Core chatbot logic
- `ncga_cleaned_evidence_content.json` - Main pages training data (20 pages)
- `ncga_articles.json` - Articles training data (704 articles)
- `requirements_streamlit.txt` - Python dependencies

## Deployment

This app can be deployed on:
- Streamlit Cloud (recommended)
- Heroku
- Vercel
- Any platform supporting Python/Streamlit 