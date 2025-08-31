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
        # Hardcoded Google Sheet ID for production deployment
        self.sheet_id = sheet_id or "7bf6bbe37a69e00be364f74d8f66773baae5244e"
        
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
                # Try to use Streamlit secrets for credentials
                try:
                    creds = Credentials.from_service_account_info({
                        "type": "service_account",
                        "project_id": st.secrets.get('GOOGLE_PROJECT_ID'),
                        "private_key_id": st.secrets.get('GOOGLE_PRIVATE_KEY_ID'),
                        "private_key": st.secrets.get('GOOGLE_PRIVATE_KEY', '').replace('\\n', '\n'),
                        "client_email": st.secrets.get('GOOGLE_CLIENT_EMAIL'),
                        "client_id": st.secrets.get('GOOGLE_CLIENT_ID'),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_x509_cert_url": st.secrets.get('GOOGLE_CLIENT_X509_CERT_URL')
                    }, scopes=scope)
                except:
                    # If no secrets available, feedback system will be disabled
                    raise Exception("Google credentials not available in Streamlit secrets")
            
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(self.sheet_id).sheet1
            
            # Initialize sheet headers if needed
            self._init_sheet_headers()
            
            print(f"✅ Connected to Google Sheet: {self.sheet.title}")
            
        except Exception as e:
            print(f"❌ Error connecting to Google Sheets: {e}")
            self.sheet = None
    
    def _init_sheet_headers(self):
        """Initialize sheet headers ensuring they're in the correct position"""
        try:
            expected_headers = [
                'Timestamp', 'User Query', 'Chatbot Response', 'Rating', 
                'Session ID', 'Response Time (ms)', 'Sources Used', 'Model Used'
            ]
            
            # Get current headers from row 1
            try:
                current_headers = self.sheet.row_values(1)
            except:
                current_headers = []
            
            # Check if headers need to be fixed
            if not current_headers or current_headers != expected_headers:
                print(f"🔧 Current headers: {current_headers}")
                print(f"🔧 Expected headers: {expected_headers}")
                
                # Clear first row if it exists and set correct headers
                if current_headers:
                    self.sheet.delete_rows(1)
                
                # Insert headers at the very beginning (row 1, column 1)
                self.sheet.insert_row(expected_headers, 1)
                print("✅ Fixed Google Sheet headers - data should now align correctly")
            else:
                print("✅ Google Sheet headers already correct")
                
        except Exception as e:
            print(f"❌ Error initializing sheet headers: {e}")
    
    def save_interaction(self, user_query: str, chatbot_response: str, 
                        session_id: str = None, response_time_ms: int = None, 
                        sources_used: str = None, model_used: str = None) -> bool:
        """Save user interaction to Google Sheets without rating (for automatic saving)"""
        if not self.sheet:
            print("❌ No Google Sheet connection available")
            return False
            
        try:
            # Check for existing entry with same query and response
            existing_row = self._find_existing_feedback(user_query, chatbot_response)
            
            if existing_row:
                # Entry already exists, don't create duplicate
                print(f"⏭️ Interaction already exists (row {existing_row['row_number']})")
                return True
            
            # Format sources_used for storage
            sources_str = ""
            if sources_used:
                if isinstance(sources_used, list):
                    sources_str = "; ".join([f"{s.get('title', '')} ({s.get('type', '')})" for s in sources_used])
                else:
                    sources_str = str(sources_used)
            
            # Add new entry without rating
            row_data = [
                datetime.now().isoformat(),
                user_query,
                chatbot_response,
                '',  # No rating initially
                session_id or '',
                response_time_ms or '',
                sources_str,
                model_used or ''
            ]
            
            # Append to sheet
            self.sheet.append_row(row_data)
            print(f"✅ Saved new interaction automatically")
            return True
            
        except Exception as e:
            print(f"❌ Error saving interaction: {e}")
            return False
    
    def update_rating(self, user_query: str, chatbot_response: str, rating: int) -> bool:
        """Update rating for an existing interaction"""
        if not self.sheet:
            print("❌ No Google Sheet connection available")
            return False
            
        try:
            # Find existing entry
            existing_row = self._find_existing_feedback(user_query, chatbot_response)
            
            if existing_row:
                # Update existing entry
                row_number = existing_row['row_number']
                self.sheet.update_cell(row_number, 4, 'Like' if rating == 1 else 'Dislike')  # Rating column
                self.sheet.update_cell(row_number, 1, datetime.now().isoformat())  # Update timestamp
                print(f"✅ Updated rating for existing entry (row {row_number}): {'Like' if rating == 1 else 'Dislike'}")
                return True
            else:
                print(f"❌ No existing interaction found to update rating")
                return False
            
        except Exception as e:
            print(f"❌ Error updating rating: {e}")
            return False

    def save_feedback(self, user_query: str, chatbot_response: str, rating: int, 
                     session_id: str = None, response_time_ms: int = None, 
                     sources_used: str = None, model_used: str = None) -> bool:
        """Save user feedback to Google Sheets (legacy method for compatibility)"""
        if not self.sheet:
            print("❌ No Google Sheet connection available")
            return False
            
        try:
            # Check for existing entry with same query and response
            existing_row = self._find_existing_feedback(user_query, chatbot_response)
            
            if existing_row:
                # Update existing entry
                return self.update_rating(user_query, chatbot_response, rating)
            else:
                # Add new entry (this shouldn't happen with new flow, but keeping for compatibility)
                # Format sources_used for storage
                sources_str = ""
                if sources_used:
                    if isinstance(sources_used, list):
                        sources_str = "; ".join([f"{s.get('title', '')} ({s.get('type', '')})" for s in sources_used])
                    else:
                        sources_str = str(sources_used)
                
                row_data = [
                    datetime.now().isoformat(),
                    user_query,
                    chatbot_response,
                    'Like' if rating == 1 else 'Dislike',
                    session_id or '',
                    response_time_ms or '',
                    sources_str,
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
                return {'total_interactions': 0, 'total_rated': 0, 'likes': 0, 'dislikes': 0, 'unrated': 0}
            
            total_interactions = len(all_data)
            likes = sum(1 for row in all_data if row.get('Rating') == 'Like')
            dislikes = sum(1 for row in all_data if row.get('Rating') == 'Dislike')
            unrated = sum(1 for row in all_data if not row.get('Rating') or row.get('Rating').strip() == '')
            total_rated = likes + dislikes
            
            # Calculate satisfaction rate based only on rated interactions
            satisfaction_rate = round(likes / max(total_rated, 1) * 100, 1) if total_rated > 0 else 0
            
            return {
                'total_interactions': total_interactions,
                'total_rated': total_rated,
                'likes': likes,
                'dislikes': dislikes,
                'unrated': unrated,
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
    
    # Create metrics - now showing 5 columns
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Interactions", stats.get('total_interactions', 0))
    
    with col2:
        st.metric("Rated", stats.get('total_rated', 0))
    
    with col3:
        st.metric("Unrated", stats.get('unrated', 0))
    
    with col4:
        st.metric("Likes", stats.get('likes', 0))
    
    with col5:
        st.metric("Satisfaction Rate", f"{stats.get('satisfaction_rate', 0)}%")
    
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