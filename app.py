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
st.sidebar.markdown("### View")
view_choice = st.sidebar.radio("Select page:", ["Practice", "Leaderboard"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Practice Focus")
subject_choice = st.sidebar.selectbox(
    "Choose a topic",
    ["Adaptive (lowest mastery)", "Aptitude", "Verbal Ability", "Data Structures"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 Your Knowledge Map")

# We fetch real scores from the backend to make the bars move!
try:
    skills = ["Aptitude", "Verbal Ability", "Data Structures"]
    score_res = requests.get(f"{BASE_URL}/mastery/report/{USER_ID}")
    if score_res.status_code == 200:
        scores = score_res.json()
    else:
        scores = {}

    for skill in skills:
        current_data = scores.get(skill, {})
        if isinstance(current_data, dict):
            current_val = current_data.get("mastery", 0.1)
            status = current_data.get("level", "Beginner")
        else:
            current_val = current_data or 0.1
            status = "Expert" if current_val > 0.7 else "Intermediate" if current_val > 0.4 else "Beginner"

        st.sidebar.write(f"**{skill}**")
        st.sidebar.progress(current_val)
        st.sidebar.caption(f"Level: {status} ({int(current_val*100)}%)")
except:
    st.sidebar.warning("Connect to FastAPI to see live progress.")

if st.sidebar.button("Log Out"):
    del st.session_state['user_id']
    st.rerun()

if view_choice == "Leaderboard":
    st.title("🏆 SkillStream Leaderboard")
    leaderboard_skill = st.selectbox(
        "Show top 10 for:",
        ["Overall", "Aptitude", "Verbal Ability", "Data Structures"],
        index=0,
    )
    label = "Overall" if leaderboard_skill == "Overall" else leaderboard_skill
    st.markdown(f"Top 10 learners by {label}")
    try:
        params = {"limit": 10, "user_id": USER_ID}
        if leaderboard_skill != "Overall":
            params["skill"] = leaderboard_skill
        lb_res = requests.get(f"{BASE_URL}/leaderboard", params=params)
        if lb_res.status_code == 200:
            lb_data = lb_res.json()
            if not lb_data.get("leaderboard"):
                st.info("No leaderboard data available for this selection yet.")
            for rank, row in enumerate(lb_data.get("leaderboard", []), start=1):
                if row["user_id"] == USER_ID:
                    st.markdown(f"**{rank}. {row['user_name']} — {int(row['points'])} pts • {row['accuracy']}% accuracy**")
                else:
                    st.write(f"{rank}. {row['user_name']} — {int(row['points'])} pts, {row['accuracy']}% accuracy")
            if lb_data.get("user_rank") is not None:
                st.markdown("---")
                st.markdown(f"**Your current rank:** {lb_data['user_rank']}")
        else:
            st.warning("Leaderboard is unavailable.")
    except Exception:
        st.warning("Could not load leaderboard.")
    st.stop()

# --- 3. THE ADAPTIVE CHALLENGE ZONE ---
st.title("🚀 SkillStream AI: Personalized Session")
if 'current_data' in st.session_state and st.session_state.current_data.get('user_level'):
    st.markdown(
        f"Welcome back, **{st.session_state.user_name}**. Current level: **{st.session_state.current_data['user_level']}**. "
        "The AI has analyzed your recent performance."
    )
else:
    st.markdown(f"Welcome back, **{st.session_state.user_name}**. The AI has analyzed your recent performance.")

if st.button("Generate My Next Challenge", type="primary"):
    with st.spinner("🔍 Scanning for knowledge gaps..."):
        params = {}
        if subject_choice != "Adaptive (lowest mastery)":
            params["skill"] = subject_choice
        res = requests.get(f"{BASE_URL}/recommend/{USER_ID}", params=params)
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
    # Show a small badge when the question is explicitly contextualized to a use case
    if q.get('context') or q.get('anchor_fact') or q.get('use_case') or q.get('use_case_description'):
        st.markdown("**Scenario-based question** — Context provided")
    
    with st.container(border=True):
        st.markdown(f"**Targeting:** `{data['skill']}` | **Difficulty:** `{data['difficulty']}`")
        display_question = q['question']
        if display_question.startswith("Context:") and "\n\n" in display_question:
            context_text, display_question = display_question.split("\n\n", 1)
            st.info(context_text)
        elif q.get('context'):
            st.info(f"Context: {q['context']}")
        st.subheader(display_question)
        
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
            st.write("✨ **Snappy Check:** No explanation needed for this level.")
            explanation = "N/A - Quick Check"
        # ---------------------------------

        if st.button("Submit My Answer"):
            payload = {
                "user_id": USER_ID,
                "user_name": st.session_state.user_name,
                "skill": data['skill'],
                "difficulty": data.get('difficulty', 'Medium'),
                "selected_option": choice,
                "correct_option": q['correct_option'],
                "question_text": q['question'],
                "selected_option_text": options[choice],
                "correct_option_text": options[q['correct_option']],
                "explanation": explanation,
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
        st.markdown(f"**Correct answer:** {res.get('correct_option')} — {res.get('correct_option_text')} ")

    expert_text = res.get('expert_feedback')
    show_expert = bool(expert_text)
    if show_expert:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🧘 The Mentor")
            st.info(res['mentor_feedback'] or "Review the correct answer and the explanation carefully.")
        with col2:
            st.markdown("### 👨‍💼 The Industry Expert")
            st.warning(expert_text or ("Good work — no additional expert notes." if res.get('is_correct') else "The student answer did not match the key reasoning behind the right choice."))
    else:
        # Show only the mentor when there is no expert feedback to display and no need to show expert
        st.markdown("### 🧘 The Mentor")
        st.info(res['mentor_feedback'] or "Review the correct answer and the explanation carefully.")
    
    mastery_delta = res.get("mastery_delta")
    if mastery_delta is None and res.get("previous_mastery") is not None:
        mastery_delta = res["new_mastery"] - res["previous_mastery"]
    st.metric(
        "New Mastery Score",
        f"{res['new_mastery']*100:.1f}%",
        delta=f"{mastery_delta*100:.1f}%" if mastery_delta is not None else None,
    )
    if res.get("points") is not None:
        st.metric("Total Points", f"{int(res['points'])}")
    
    if st.button("Ready for the next one?"):
        del st.session_state['last_result']
        st.rerun()
