#!/usr/bin/env python3
"""
Feedback System for NCGA Chatbot
Handles user ratings and saves to Google Sheets.
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st
import os

class FeedbackSystem:
    def __init__(self, credentials_file: str = None, sheet_id: str = None):
        """Initialize the feedback system with Google Sheets connection"""
        self.credentials_file = credentials_file
        self.sheet_id = sheet_id or os.getenv('GOOGLE_SHEET_ID')
        
        if not self.sheet_id:
            print("⚠️ No Google Sheet ID provided. Feedback will not be saved.")
            self.sheet = None
            return
            
        try:
            # Set up Google Sheets API
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            if credentials_file and os.path.exists(credentials_file):
                creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
            else:
                # Try to use environment variables for credentials
                creds = Credentials.from_service_account_info({
                    "type": "service_account",
                    "project_id": os.getenv('GOOGLE_PROJECT_ID'),
                    "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID'),
                    "private_key": os.getenv('GOOGLE_PRIVATE_KEY', '').replace('\\n', '\n'),
                    "client_email": os.getenv('GOOGLE_CLIENT_EMAIL'),
                    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.getenv('GOOGLE_CLIENT_X509_CERT_URL')
                }, scopes=scope)
            
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(self.sheet_id).sheet1
            
            # Initialize sheet headers if needed
            self._init_sheet_headers()
            
            print(f"✅ Connected to Google Sheet: {self.sheet.title}")
            
        except Exception as e:
            print(f"❌ Error connecting to Google Sheets: {e}")
            self.sheet = None
    
    def _init_sheet_headers(self):
        """Initialize sheet headers if the sheet is empty"""
        try:
            headers = self.sheet.row_values(1)
            if not headers:
                # Add headers
                headers = [
                    'Timestamp', 'User Query', 'Chatbot Response', 'Rating', 
                    'Session ID', 'Response Time (ms)', 'Sources Used', 'Model Used'
                ]
                self.sheet.append_row(headers)
                print("✅ Initialized Google Sheet headers")
        except Exception as e:
            print(f"❌ Error initializing sheet headers: {e}")
    
    def save_feedback(self, user_query: str, chatbot_response: str, rating: int, 
                     session_id: str = None, response_time_ms: int = None, 
                     sources_used: str = None, model_used: str = None) -> bool:
        """Save user feedback to Google Sheets"""
        if not self.sheet:
            print("❌ No Google Sheet connection available")
            return False
            
        try:
            # Check for existing entry with same query and response
            existing_row = self._find_existing_feedback(user_query, chatbot_response)
            
            if existing_row:
                # Update existing entry
                row_number = existing_row['row_number']
                self.sheet.update_cell(row_number, 4, 'Like' if rating == 1 else 'Dislike')  # Rating column
                self.sheet.update_cell(row_number, 1, datetime.now().isoformat())  # Timestamp column
                print(f"✅ Updated existing feedback entry (row {row_number}) with rating: {'Like' if rating == 1 else 'Dislike'}")
            else:
                # Add new entry
                row_data = [
                    datetime.now().isoformat(),
                    user_query,
                    chatbot_response,
                    'Like' if rating == 1 else 'Dislike',
                    session_id or '',
                    response_time_ms or '',
                    sources_used or '',
                    model_used or ''
                ]
                
                # Append to sheet
                self.sheet.append_row(row_data)
                print(f"✅ Created new feedback entry with rating: {'Like' if rating == 1 else 'Dislike'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving feedback: {e}")
            return False
    
    def _find_existing_feedback(self, user_query: str, chatbot_response: str) -> dict:
        """Find existing feedback entry with same query and response"""
        try:
            # Get all data
            all_data = self.sheet.get_all_records()
            
            # Look for matching query and response
            for i, row in enumerate(all_data, start=2):  # start=2 because row 1 is headers
                if (row.get('User Query') == user_query and 
                    row.get('Chatbot Response') == chatbot_response):
                    return {'row_number': i, 'data': row}
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding existing feedback: {e}")
            return None
    
    def get_feedback_stats(self) -> Dict:
        """Get feedback statistics from Google Sheets"""
        if not self.sheet:
            return {}
            
        try:
            # Get all data
            all_data = self.sheet.get_all_records()
            
            if not all_data:
                return {'total_feedback': 0, 'likes': 0, 'dislikes': 0}
            
            total_feedback = len(all_data)
            likes = sum(1 for row in all_data if row.get('Rating') == 'Like')
            dislikes = sum(1 for row in all_data if row.get('Rating') == 'Dislike')
            
            satisfaction_rate = round(likes / max(total_feedback, 1) * 100, 1)
            
            return {
                'total_feedback': total_feedback,
                'likes': likes,
                'dislikes': dislikes,
                'satisfaction_rate': satisfaction_rate
            }
            
        except Exception as e:
            print(f"❌ Error getting feedback stats: {e}")
            return {}
    
    def get_recent_feedback(self, limit: int = 10) -> List[Dict]:
        """Get recent feedback entries from Google Sheets"""
        if not self.sheet:
            return []
            
        try:
            # Get all data and return most recent
            all_data = self.sheet.get_all_records()
            
            # Sort by timestamp (assuming it's in the first column)
            sorted_data = sorted(all_data, key=lambda x: x.get('Timestamp', ''), reverse=True)
            
            return sorted_data[:limit]
            
        except Exception as e:
            print(f"❌ Error getting recent feedback: {e}")
            return []

# Streamlit UI Components
def render_feedback_buttons(user_query: str, chatbot_response: str, 
                          session_id: str = None, response_time_ms: int = None,
                          sources_used: str = None, model_used: str = None):
    """Render like/dislike buttons in Streamlit"""
    
    # Initialize feedback system
    feedback_system = FeedbackSystem()
    
    # Simple inline layout - buttons right next to each other
    st.write("**Was this response helpful?**")
    
    # Use a single row with buttons side by side
    like_col, dislike_col, spacer = st.columns([1, 1, 8])
    
    with like_col:
        if st.button("👍 Like", key=f"like_{hash(user_query)}"):
            print(f"DEBUG: Like button clicked!")
            success = feedback_system.save_feedback(
                user_query=user_query,
                chatbot_response=chatbot_response,
                rating=1,
                session_id=session_id,
                response_time_ms=response_time_ms,
                sources_used=sources_used,
                model_used=model_used
            )
            print(f"DEBUG: Like save result: {success}")
            if success:
                st.success("Thank you! 👍")
            else:
                st.error("Failed to save.")
    
    with dislike_col:
        if st.button("👎 Dislike", key=f"dislike_{hash(user_query)}"):
            print(f"DEBUG: Dislike button clicked!")
            success = feedback_system.save_feedback(
                user_query=user_query,
                chatbot_response=chatbot_response,
                rating=0,
                session_id=session_id,
                response_time_ms=response_time_ms,
                sources_used=sources_used,
                model_used=model_used
            )
            print(f"DEBUG: Dislike save result: {success}")
            if success:
                st.success("Thank you! 👎")
            else:
                st.error("Failed to save.")

def render_feedback_dashboard():
    """Render feedback analytics dashboard"""
    feedback_system = FeedbackSystem()
    stats = feedback_system.get_feedback_stats()
    
    if not stats:
        st.warning("No feedback data available yet.")
        return
    
    st.subheader("📊 Feedback Analytics")
    
    # Create metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Feedback", stats['total_feedback'])
    
    with col2:
        st.metric("Satisfaction Rate", f"{stats['satisfaction_rate']}%")
    
    with col3:
        st.metric("Likes", stats['likes'])
    
    with col4:
        st.metric("Dislikes", stats['dislikes'])
    
    # Recent feedback
    st.subheader("📝 Recent Feedback")
    recent_feedback = feedback_system.get_recent_feedback(5)
    
    if recent_feedback:
        for feedback in recent_feedback:
            with st.expander(f"{feedback.get('Timestamp', '')[:19]} - {'👍' if feedback.get('Rating') == 'Like' else '👎'}"):
                st.write(f"**Query:** {feedback.get('User Query', '')}")
                st.write(f"**Response:** {feedback.get('Chatbot Response', '')[:200]}...")
    
    else:
        st.info("No recent feedback found.") 