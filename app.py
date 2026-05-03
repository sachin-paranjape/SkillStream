import streamlit as st
import requests
import pandas as pd

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="SkillStream AI", layout="wide", initial_sidebar_state="expanded")

# --- 1. USER AUTHENTICATION & SESSION MANAGEMENT ---
if 'user_id' not in st.session_state:
    st.title("🛡️ SkillStream Login")
    user_name = st.text_input("Enter your Username or Student ID to begin:")
    if st.button("Start Learning"):
        if user_name:
            # We hash the name to a unique ID for the BKT engine
            st.session_state.user_id = sum(ord(c) for c in user_name) 
            st.session_state.user_name = user_name
            st.rerun()
    st.stop()

USER_ID = st.session_state.user_id

# --- 2. SIDEBAR: THE REAL-TIME BRAIN MAP ---
st.sidebar.title(f"👤 {st.session_state.user_name}")
st.sidebar.caption(f"Student ID: {USER_ID}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 Your Knowledge Map")

# We fetch real scores from the backend to make the bars move!
try:
    # This assumes you have an endpoint that returns all scores, 
    # or we can call your audit_mastery logic
    skills = ["Aptitude", "Verbal Ability", "Data Structures"]
    for skill in skills:
        # We manually fetch the score for each skill to keep the sidebar updated
        score_res = requests.get(f"{BASE_URL}/mastery/report/{USER_ID}") # Or your specific audit endpoint
        if score_res.status_code == 200:
            scores = score_res.json()
            # If the skill hasn't been started yet, default to 0.1
            current_val = scores.get(skill, 0.1)
        else:
            current_val = 0.1
            
        st.sidebar.write(f"**{skill}**")
        st.sidebar.progress(current_val)
        status = "Expert" if current_val > 0.7 else "Intermediate" if current_val > 0.4 else "Beginner"
        st.sidebar.caption(f"Level: {status} ({int(current_val*100)}%)")
except:
    st.sidebar.warning("Connect to FastAPI to see live progress.")

if st.sidebar.button("Log Out"):
    del st.session_state['user_id']
    st.rerun()

# --- 3. THE ADAPTIVE CHALLENGE ZONE ---
st.title("🚀 SkillStream AI: Personalized Session")
st.markdown(f"Welcome back, **{st.session_state.user_name}**. The AI has analyzed your recent performance.")

if st.button("Generate My Next Challenge", type="primary"):
    with st.spinner("🔍 Scanning for knowledge gaps..."):
        res = requests.get(f"{BASE_URL}/recommend/{USER_ID}")
        if res.status_code == 200:
            st.session_state.current_data = res.json()
            # Clear previous results when a new question is generated
            if 'last_result' in st.session_state:
                del st.session_state['last_result']
            st.rerun()

# --- 4. QUESTION DISPLAY & CONDITIONAL LOGIC ---
if 'current_data' in st.session_state:
    data = st.session_state.current_data
    q = data['question']
    
    with st.container(border=True):
        st.markdown(f"**Targeting:** `{data['skill']}` | **Difficulty:** `{data['difficulty']}`")
        st.subheader(q['question'])
        
        # MCQ Options
        options = q['options']
        choice = st.radio("Choose the best answer:", options=list(options.keys()), 
                        format_func=lambda x: f"{x}) {options[x]}")

        # --- THE NEW CONDITIONAL LOGIC ---
        # This replaces the old 'Why' box logic
        if data.get('needs_explanation', True):
            explanation = st.text_area("🧠 Socratic Insight: Explain your logic briefly:", 
                                      placeholder="Why is this the correct logical path?")
        else:
            st.write("✨ **Snappy Check:** No explanation needed for this verbal level.")
            explanation = "N/A - Quick Check"
        # ---------------------------------

        if st.button("Submit My Answer"):
            payload = {
                "user_id": USER_ID,
                "skill": data['skill'],
                "selected_option": choice,
                "correct_option": q['correct_option'],
                "explanation_text": explanation,
                "difficulty": data['difficulty']
            }
            
            with st.spinner("Consulting the Mentor & Expert..."):
                ans_res = requests.post(f"{BASE_URL}/submit", json=payload)
                if ans_res.status_code == 200:
                    st.session_state.last_result = ans_res.json()
                    # Clean up the question so they can't submit twice
                    del st.session_state['current_data']
                    st.rerun()

# --- 5. DUAL-PERSONA FEEDBACK DISPLAY ---
if 'last_result' in st.session_state:
    res = st.session_state.last_result
    
    if res['is_correct']:
        st.balloons()
        st.success("🎯 **Excellent Work!**")
    else:
        st.error("📉 **Not quite there yet.** Review the insights below.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🧘 The Mentor")
        st.info(res['mentor_feedback'])
    with col2:
        st.markdown("### 👨‍💼 The Industry Expert")
        st.warning(res['expert_feedback'])
    
    st.metric("New Mastery Score", f"{res['new_mastery']*100:.1f}%", 
              delta=f"{(res['new_mastery'] - 0.1)*100:.1f}%" if res['is_correct'] else None)
    
    if st.button("Ready for the next one?"):
        del st.session_state['last_result']
        st.rerun()