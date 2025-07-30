# 🌽 NCGA Chatbot

A web-based chatbot trained on National Corn Growers Association (NCGA) public info that provides evidence-backed responses about NCGA Policies, Publications, and News
## Features

- **Evidence-backed responses** - All information is cited from NCGA content
- **Web interface** - Easy to use on any device
- **Secure API handling** - Users provide their own OpenAI API keys
- **Comprehensive knowledge** - Expert on all things NCGA

## How to Use

1. Visit the deployed app URL
2. Enter your OpenAI API key in the sidebar
3. Start asking questions about NCGA / related topics!

## Technical Details

- Uses OpenAI GPT-4o for response generation
- RAG (Retrieval-Augmented Generation) architecture
- Evidence matching to prevent hallucinations

## Files

- `README.md` - Project documentation
- `ncga_articles.json` - Articles training data (704 articles)
- `ncga_chatbot.py` - Core chatbot logic
- `ncga_cleaned_evidence_content.json` - Main pages training data (20 pages)
- `ncga_policy_content.json` - Policy documents training data (56 sections)
- `requirements.txt` - Python dependencies
- `streamlit_app.py` - Streamlit web application

## Deployment

This app can be deployed on:
- Streamlit Cloud (recommended)
- Heroku
- Vercel
- Any platform supporting Python/Streamlit 
