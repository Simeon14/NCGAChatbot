# Google Sheets Setup for Feedback System

## Step 1: Create a Google Sheet
1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new spreadsheet
3. Name it "NCGA Chatbot Feedback"
4. Copy the Sheet ID from the URL (the long string between /d/ and /edit)

## Step 2: Set up Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable Google Sheets API and Google Drive API
4. Create a Service Account
5. Download the JSON credentials file

## Step 3: Configure Environment Variables
Add these to your Streamlit secrets or environment variables:

```toml
# In .streamlit/secrets.toml or environment variables
GOOGLE_SHEET_ID = "your_sheet_id_here"
GOOGLE_PROJECT_ID = "your_project_id"
GOOGLE_PRIVATE_KEY_ID = "your_private_key_id"
GOOGLE_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GOOGLE_CLIENT_EMAIL = "your_service_account@project.iam.gserviceaccount.com"
GOOGLE_CLIENT_ID = "your_client_id"
GOOGLE_CLIENT_X509_CERT_URL = "https://www.googleapis.com/robot/v1/metadata/x509/your_service_account%40project.iam.gserviceaccount.com"
```

## Step 4: Share the Google Sheet
1. Open your Google Sheet
2. Click "Share" button
3. Add your service account email (from GOOGLE_CLIENT_EMAIL)
4. Give it "Editor" permissions

## Step 5: Test the Integration
The feedback system will automatically:
- Connect to your Google Sheet
- Create headers if the sheet is empty
- Save all feedback as new rows
- Provide analytics on feedback data

## Notes
- The sheet will have columns: Timestamp, User Query, Chatbot Response, Rating, Session ID, Response Time (ms), Sources Used, Model Used
- All feedback is saved in real-time
- Only you can access the sheet (users can't see it)
- Data is automatically backed up by Google 