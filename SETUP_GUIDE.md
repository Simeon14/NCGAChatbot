# 🔑 API Key Setup Guide

## **For Local Development**

### Option 1: Environment Variable (Recommended)
```bash
# Add to your shell profile (~/.zshrc, ~/.bashrc, etc.)
export OPENAI_API_KEY="your-api-key-here"

# Then restart your terminal or run:
source ~/.zshrc
```

### Option 2: .env File
Create a `.env` file in the project directory:
```
OPENAI_API_KEY=your-api-key-here
```

## **For Streamlit Cloud Deployment**

### Option 1: Streamlit Secrets (Recommended)
1. Go to your app on Streamlit Cloud
2. Click "Settings" → "Secrets"
3. Add your API key:
```toml
OPENAI_API_KEY = "your-api-key-here"
```

### Option 2: Environment Variables
1. Go to your app on Streamlit Cloud
2. Click "Settings" → "General"
3. Add environment variable:
   - **Name:** `OPENAI_API_KEY`
   - **Value:** `your-api-key-here`

## **For Other Users**

Users can simply:
1. Visit your deployed app URL
2. Enter their own API key in the sidebar
3. Start chatting!

**No setup required for end users!**

## **Security Notes**

- ✅ API keys are never stored in the code
- ✅ Each user provides their own key
- ✅ Keys are not shared between users
- ✅ Environment variables are secure
- ✅ Streamlit secrets are encrypted

## **Getting an OpenAI API Key**

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Use it in the app!

**Cost:** ~$0.002 per 1K tokens (very affordable for casual use) 