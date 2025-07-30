#!/usr/bin/env python3
"""
Feedback System for NCGA Chatbot
Handles user ratings, database storage, and feedback analytics.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import streamlit as st

class FeedbackSystem:
    def __init__(self, db_path: str = None):
        """Initialize the feedback system with database connection"""
        if db_path is None:
            # Try to find the database in the data directory relative to the deploy folder
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to NCGA directory, then into data folder
            data_dir = os.path.join(os.path.dirname(current_dir), 'data')
            db_path = os.path.join(data_dir, 'feedback.db')
            
            # Create data directory if it doesn't exist
            os.makedirs(data_dir, exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with feedback table"""
        try:
            cursor = self.conn.cursor()
            
            # Create feedback table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_query TEXT NOT NULL,
                    chatbot_response TEXT NOT NULL,
                    rating INTEGER NOT NULL,  -- 1 for like, 0 for dislike
                    feedback_comment TEXT,
                    session_id TEXT,
                    response_time_ms INTEGER,
                    sources_used TEXT,  -- JSON string of sources
                    model_used TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON feedback(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_rating 
                ON feedback(rating)
            ''')
            
            self.conn.commit()
            
            print(f"Feedback database initialized: {self.db_path}")
            
        except Exception as e:
            print(f"Error initializing feedback database: {e}")
    
    def __del__(self):
        """Clean up database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def save_feedback(self, user_query: str, chatbot_response: str, rating: int, 
                     session_id: str = None, response_time_ms: int = None, 
                     sources_used: str = None, model_used: str = None) -> bool:
        """Save user feedback to the database"""
        try:
            # Check if an entry with the same query and response already exists
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id FROM feedback 
                WHERE user_query = ? AND chatbot_response = ?
            """, (user_query, chatbot_response))
            
            existing_entry = cursor.fetchone()
            
            if existing_entry:
                # Update existing entry
                cursor.execute("""
                    UPDATE feedback 
                    SET rating = ?, timestamp = ?, session_id = ?, 
                        response_time_ms = ?, sources_used = ?, model_used = ?
                    WHERE id = ?
                """, (rating, datetime.now().isoformat(), session_id, 
                      response_time_ms, sources_used, model_used, existing_entry[0]))
                print(f"DEBUG: Updated existing feedback entry {existing_entry[0]} with rating {rating}")
            else:
                # Insert new entry
                cursor.execute("""
                    INSERT INTO feedback (user_query, chatbot_response, rating, timestamp, 
                                       session_id, response_time_ms, sources_used, model_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_query, chatbot_response, rating, datetime.now().isoformat(),
                      session_id, response_time_ms, sources_used, model_used))
                print(f"DEBUG: Created new feedback entry with rating {rating}")
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False
    
    def get_feedback_stats(self) -> Dict:
        """Get feedback statistics"""
        try:
            cursor = self.conn.cursor()
            
            # Total feedback count
            cursor.execute("SELECT COUNT(*) FROM feedback")
            total_feedback = cursor.fetchone()[0]
            
            # Rating breakdown
            cursor.execute("SELECT rating, COUNT(*) FROM feedback GROUP BY rating")
            rating_breakdown = dict(cursor.fetchall())
            
            # Recent feedback (last 7 days)
            cursor.execute('''
                SELECT COUNT(*) FROM feedback 
                WHERE timestamp >= datetime('now', '-7 days')
            ''')
            recent_feedback = cursor.fetchone()[0]
            
            # Average response time
            cursor.execute('''
                SELECT AVG(response_time_ms) FROM feedback 
                WHERE response_time_ms IS NOT NULL
            ''')
            avg_response_time = cursor.fetchone()[0] or 0
            
            return {
                'total_feedback': total_feedback,
                'likes': rating_breakdown.get(1, 0),
                'dislikes': rating_breakdown.get(0, 0),
                'recent_feedback': recent_feedback,
                'avg_response_time_ms': round(avg_response_time, 2),
                'satisfaction_rate': round(rating_breakdown.get(1, 0) / max(total_feedback, 1) * 100, 1)
            }
            
        except Exception as e:
            print(f"Error getting feedback stats: {e}")
            return {}
    
    def get_recent_feedback(self, limit: int = 10) -> List[Dict]:
        """Get recent feedback entries"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, user_query, chatbot_response, rating, 
                       feedback_comment, response_time_ms
                FROM feedback 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            
            feedback_list = []
            for row in results:
                feedback_list.append({
                    'timestamp': row[0],
                    'user_query': row[1],
                    'chatbot_response': row[2],
                    'rating': row[3],
                    'feedback_comment': row[4],
                    'response_time_ms': row[5]
                })
            
            return feedback_list
            
        except Exception as e:
            print(f"Error getting recent feedback: {e}")
            return []
    
    def get_problematic_queries(self, min_dislikes: int = 2) -> List[Dict]:
        """Get queries that received multiple dislikes"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('''
                SELECT user_query, COUNT(*) as dislike_count,
                       GROUP_CONCAT(chatbot_response, ' || ') as responses
                FROM feedback 
                WHERE rating = 0 
                GROUP BY user_query 
                HAVING COUNT(*) >= ?
                ORDER BY dislike_count DESC
            ''', (min_dislikes,))
            
            results = cursor.fetchall()
            
            problematic_queries = []
            for row in results:
                problematic_queries.append({
                    'query': row[0],
                    'dislike_count': row[1],
                    'responses': row[2].split(' || ')
                })
            
            return problematic_queries
            
        except Exception as e:
            print(f"Error getting problematic queries: {e}")
            return []
    
    def export_feedback_data(self, filepath: str = "feedback_export.json"):
        """Export all feedback data to JSON file"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('SELECT * FROM feedback')
            results = cursor.fetchall()
            
            # Get column names
            cursor.execute('PRAGMA table_info(feedback)')
            columns = [col[1] for col in cursor.fetchall()]
            
            # Convert to list of dictionaries
            data = []
            for row in results:
                data.append(dict(zip(columns, row)))
            
            # Save to JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"Feedback data exported to: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting feedback data: {e}")
            return False

# Streamlit UI Components
def render_feedback_buttons(user_query: str, chatbot_response: str, 
                          session_id: str = None, response_time_ms: int = None,
                          sources_used: List[Dict] = None, model_used: str = None):
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
            with st.expander(f"{feedback['timestamp'][:19]} - {'👍' if feedback['rating'] == 1 else '👎'}"):
                st.write(f"**Query:** {feedback['user_query']}")
                st.write(f"**Response:** {feedback['chatbot_response'][:200]}...")
                if feedback['feedback_comment']:
                    st.write(f"**Comment:** {feedback['feedback_comment']}")
    
    # Problematic queries
    st.subheader("⚠️ Queries with Multiple Dislikes")
    problematic_queries = feedback_system.get_problematic_queries()
    
    if problematic_queries:
        for query_data in problematic_queries:
            with st.expander(f"'{query_data['query']}' ({query_data['dislike_count']} dislikes)"):
                st.write(f"**Query:** {query_data['query']}")
                st.write("**Responses that received dislikes:**")
                for i, response in enumerate(query_data['responses'][:3], 1):
                    st.write(f"{i}. {response[:150]}...")
    else:
        st.info("No queries with multiple dislikes found.")
    
    # Export button
    if st.button("📥 Export Feedback Data"):
        if feedback_system.export_feedback_data():
            st.success("Feedback data exported successfully!")
        else:
            st.error("Failed to export feedback data.") 