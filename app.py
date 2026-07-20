import streamlit as st
from database import init_db, get_connection
from ui_components import (
    inject_glassmorphic_css,
    render_login_screen,
    render_header,
    render_sidebar,
    render_main_challenge_area,
    render_leaderboard,
)

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8600"

st.set_page_config(page_title="SkillStream AI", layout="wide", initial_sidebar_state="expanded")

# --- DATABASE PERSISTENCE & INITIALIZATION ---
init_db()
if 'db_conn' not in st.session_state:
    st.session_state.db_conn = get_connection()

# --- AUTHENTICATION ENFORCEMENT & REDIRECT ---
if not st.session_state.get('authenticated'):
    render_login_screen()
    st.stop()

# --- SESSION USER IDENTIFICATION ---
username = st.session_state.get('username', 'learner')
user_id = st.session_state.get('user_id', sum(ord(c) for c in username))
st.session_state.user_name = username
st.session_state.user_id = user_id

# --- INJECT GLASSMORPHIC DESIGN SYSTEM & HIDE STREAMLIT UI ---
inject_glassmorphic_css()

# Determine user level for header badge
current_level = None
if 'current_data' in st.session_state and st.session_state.current_data.get('user_level'):
    current_level = st.session_state.current_data['user_level']

# --- HEADER COMPONENT ---
render_header(username, current_level)

# --- SIDEBAR COMPONENT (COLUMN 1) ---
view_choice, subject_choice, scores = render_sidebar(username, user_id, BASE_URL)

# --- PRIMARY CONTENT CANVAS (COLUMN 2) ---
if view_choice == "Leaderboard":
    render_leaderboard(BASE_URL, user_id)
else:
    render_main_challenge_area(username, subject_choice, BASE_URL, user_id)
