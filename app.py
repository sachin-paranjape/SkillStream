import yaml
import streamlit as st
import streamlit_authenticator as stauth
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

# --- DATABASE PERSISTENCE ---
init_db()
if 'db_conn' not in st.session_state:
    st.session_state.db_conn = get_connection()

# --- AUTHENTICATION CONFIG ---
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- AUTHENTICATION ENFORCEMENT & REDIRECT ---
if not st.session_state.get('authentication_status'):
    render_login_screen(authenticator)
    if st.session_state.get('authentication_status') is False:
        st.error("Invalid Username or Password.")
    st.stop()

# --- SESSION USER IDENTIFICATION ---
username = st.session_state.get('username', 'user')
user_name = st.session_state.get('name', username)
st.session_state.user_name = user_name
st.session_state.user_id = sum(ord(c) for c in username)
USER_ID = st.session_state.user_id

# --- INJECT GLASSMORPHIC DESIGN SYSTEM & HIDE STREAMLIT UI ---
inject_glassmorphic_css()

# Determine user level for header badge
current_level = None
if 'current_data' in st.session_state and st.session_state.current_data.get('user_level'):
    current_level = st.session_state.current_data['user_level']

# --- HEADER COMPONENT ---
render_header(user_name, current_level)

# --- SIDEBAR COMPONENT (COLUMN 1) ---
view_choice, subject_choice, scores = render_sidebar(authenticator, user_name, USER_ID, BASE_URL)

# --- PRIMARY CONTENT CANVAS (COLUMN 2) ---
if view_choice == "Leaderboard":
    render_leaderboard(BASE_URL, USER_ID)
else:
    render_main_challenge_area(user_name, subject_choice, BASE_URL, USER_ID)
