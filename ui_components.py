import streamlit as st
import pandas as pd
import requests
from auth import AuthHandler

def _html(code: str):
    """Cleanly renders raw HTML without multiline Markdown parsing bugs or ghost div leaks."""
    clean_code = " ".join(line.strip() for line in code.strip().splitlines())
    st.markdown(clean_code, unsafe_allow_html=True)

def inject_glassmorphic_css():
    """Injects high-fidelity Glassmorphic dark theme CSS and hides Streamlit default UI elements."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    /* Permanently Hide Streamlit Default Header, Menu, Deploy Button & Footer */
    #MainMenu, header, footer, [data-testid="stHeader"], [data-testid="stToolbar"], .stAppDeployButton, [data-testid="stDecoration"] {
        visibility: hidden !important;
        display: none !important;
        height: 0 !important;
    }

    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
        background: linear-gradient(135deg, #090d16 0%, #111827 40%, #1e1b4b 100%) !important;
        background-attachment: fixed !important;
        color: #f1f5f9 !important;
    }

    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }

    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.6) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.12) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3);
    }

    /* Container Border Wrappers & Forms (Frosted Glass Cards) */
    [data-testid="stVerticalBlockBorderWrapper"], .glass-card, [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.16) !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
        margin-bottom: 1rem !important;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:hover, .glass-card:hover {
        border-color: rgba(255, 255, 255, 0.28) !important;
        box-shadow: 0 12px 36px 0 rgba(99, 102, 241, 0.2) !important;
    }

    /* Frosted Glass Dataframe / Table Container */
    [data-testid="stDataFrame"], .stDataFrame {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 14px !important;
        padding: 0.4rem !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35) !important;
    }

    /* Headings & Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.02em !important;
        color: #ffffff !important;
    }

    .gradient-text {
        background: linear-gradient(135deg, #a5b4fc 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }

    .badge-glow {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        background: rgba(99, 102, 241, 0.2);
        color: #818cf8;
        border: 1px solid rgba(129, 140, 248, 0.4);
    }

    .badge-easy {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(52, 211, 153, 0.15);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.35);
    }
    .badge-medium {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(251, 191, 36, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.35);
    }
    .badge-hard {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(248, 113, 113, 0.15);
        color: #f87171;
        border: 1px solid rgba(248, 113, 113, 0.35);
    }
    .badge-expert {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(192, 132, 252, 0.15);
        color: #c084fc;
        border: 1px solid rgba(192, 132, 252, 0.35);
    }

    /* Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.85) 0%, rgba(79, 70, 229, 0.95) 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.65rem 1.4rem !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.35) !important;
        width: 100% !important;
    }

    div.stButton > button:hover {
        background: linear-gradient(135deg, rgba(129, 140, 248, 0.95) 0%, rgba(99, 102, 241, 1) 100%) !important;
        box-shadow: 0 6px 22px rgba(99, 102, 241, 0.5) !important;
        transform: translateY(-1px) !important;
    }

    /* Form Fields */
    .stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 10px !important;
        color: #f8fafc !important;
        backdrop-filter: blur(8px) !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 10px rgba(129, 140, 248, 0.4) !important;
    }

    /* Metric boxes */
    [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        color: #a5b4fc !important;
    }

    /* Progress bar */
    div.stProgress > div > div > div > div {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%) !important;
        border-radius: 10px !important;
    }

    /* Radio button options styling */
    div[role="radiogroup"] > label {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
        padding: 0.65rem 1rem !important;
        margin-bottom: 0.5rem !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }

    div[role="radiogroup"] > label:hover {
        background: rgba(99, 102, 241, 0.15) !important;
        border-color: rgba(129, 140, 248, 0.4) !important;
    }

    /* Mobile Responsiveness Rules */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
            padding-top: 1rem !important;
        }
        div.stButton > button {
            padding: 0.5rem 1rem !important;
        }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_login_screen():
    """Renders a clean glassmorphic login & registration screen using SQLite AuthHandler."""
    inject_glassmorphic_css()
    
    _html(
        """
        <div style="max-width: 440px; margin: 30px auto 1.25rem auto; text-align: center;">
            <div style="font-size: 2.8rem; margin-bottom: 0.2rem;">⚡</div>
            <h1 style="margin: 0; font-size: 2.2rem;" class="gradient-text">SkillStream AI</h1>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-top: 0.3rem;">
                Adaptive Knowledge & Dynamic Learning Engine
            </p>
        </div>
        """
    )
    
    col1, col2, col3 = st.columns([1, 2.2, 1])
    with col2:
        with st.container(border=True):
            tab_signin, tab_signup = st.tabs(["🔐 Sign In", "✨ Sign Up"])
            
            # --- TAB 1: SIGN IN ---
            with tab_signin:
                with st.form("signin_form", clear_on_submit=False):
                    username_or_email = st.text_input("Username or Email", placeholder="admin")
                    password = st.text_input("Password", type="password", placeholder="••••••••")
                    submitted = st.form_submit_button("Sign In", type="primary")
                    
                    if submitted:
                        user_dict, message = AuthHandler.authenticate_user(username_or_email, password)
                        if user_dict:
                            st.session_state.authenticated = True
                            st.session_state.username = user_dict['username']
                            st.session_state.user_name = user_dict['username']
                            st.session_state.user_id = user_dict['user_id']
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

            # --- TAB 2: SIGN UP ---
            with tab_signup:
                with st.form("signup_form", clear_on_submit=False):
                    new_username = st.text_input("Username", placeholder="new_learner")
                    new_email = st.text_input("Email Address", placeholder="learner@example.com")
                    new_password = st.text_input("Create Password", type="password", placeholder="••••••••")
                    confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••")
                    reg_submitted = st.form_submit_button("Create Account", type="primary")
                    
                    if reg_submitted:
                        if new_password != confirm_password:
                            st.error("Passwords do not match.")
                        else:
                            success, message = AuthHandler.register_user(new_username, new_email, new_password)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
        
        _html(
            """
            <div style="text-align: center; margin-top: 1.2rem; color: #64748b; font-size: 0.8rem;">
                SkillStream AI • Powered by SQLite & bcrypt Security
            </div>
            """
        )


def render_header(user_name, current_level=None):
    """Renders sleek top glassmorphic banner header with user context."""
    level_badge = f"<span class='badge-glow'>{current_level}</span>" if current_level else ""
    _html(
        f"""
        <div class="glass-card" style="padding: 1.1rem 1.5rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem;">
                <div style="display: flex; align-items: center; gap: 0.6rem;">
                    <span style="font-size: 1.5rem; font-weight: 700;" class="gradient-text">⚡ SkillStream AI</span>
                    <span style="color: #64748b; font-size: 0.85rem;">| Practice Workspace</span>
                </div>
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="color: #cbd5e1; font-size: 0.9rem;">Learner: <strong>{user_name}</strong></span>
                    {level_badge}
                </div>
            </div>
        </div>
        """
    )


def render_sidebar(user_name, user_id, base_url):
    """Renders the sleek sidebar for settings, navigation, topic focus, and live mastery map."""
    _html(
        f"""
        <div style="text-align: center; padding-bottom: 0.8rem; border-bottom: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 2rem; margin-bottom: 0.1rem;">👤</div>
            <h3 style="margin:0; font-size: 1.15rem; color: #f8fafc;">{user_name}</h3>
            <span style="font-size: 0.75rem; color: #94a3b8;">Student ID: {user_id}</span>
        </div>
        """
    )
    
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    st.sidebar.markdown("#### 📍 Navigation")
    view_choice = st.sidebar.radio("Select View:", ["Practice", "Leaderboard"], label_visibility="collapsed")

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🎯 Focus Topic")
    subject_choice = st.sidebar.selectbox(
        "Choose a topic",
        ["Adaptive (lowest mastery)", "Aptitude", "Verbal Ability", "Data Structures"],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🧠 Knowledge Mastery Map")

    scores = {}
    try:
        skills = ["Aptitude", "Verbal Ability", "Data Structures"]
        score_res = requests.get(f"{base_url}/mastery/report/{user_id}", timeout=3)
        if score_res.status_code == 200:
            scores = score_res.json()
        
        for skill in skills:
            current_data = scores.get(skill, {})
            if isinstance(current_data, dict):
                current_val = current_data.get("mastery", 0.1)
                status = current_data.get("level", "Beginner")
            else:
                current_val = current_data or 0.1
                status = "Expert" if current_val > 0.7 else "Intermediate" if current_val > 0.4 else "Beginner"

            st.sidebar.markdown(
                f"<div style='font-size:0.85rem; font-weight:600; color:#e2e8f0; margin-top:0.4rem;'>{skill}</div>",
                unsafe_allow_html=True
            )
            st.sidebar.progress(current_val)
            st.sidebar.caption(f"{status} • {int(current_val*100)}%")
    except Exception:
        st.sidebar.warning("Live progress offline.")

    st.sidebar.markdown("---")
    
    if st.sidebar.button("Log Out"):
        st.session_state.authenticated = False
        if 'user_name' in st.session_state:
            del st.session_state['user_name']
        if 'user_id' in st.session_state:
            del st.session_state['user_id']
        st.rerun()
    
    return view_choice, subject_choice, scores


def render_main_challenge_area(user_name, subject_choice, base_url, user_id):
    """Main Content Canvas: De-cluttered full-width challenge generator & MCQ workspace."""
    has_active_question = ('current_data' in st.session_state) or ('current_question' in st.session_state)
    has_active_result = ('last_result' in st.session_state)

    # --- Conditional Challenge Generation Button Card ---
    if not has_active_question and not has_active_result:
        with st.container(border=True):
            _html("<h3 style='margin-top: 0;'>🚀 Adaptive Challenge Hub</h3>")
            
            st.markdown(f"Welcome, **{user_name}**. Generate a challenge tailored to your skill mastery level.")

            if st.button("✨ Generate My Next Challenge", type="primary", use_container_width=True):
                with st.spinner("🔍 Analyzing knowledge gaps..."):
                    params = {}
                    if subject_choice != "Adaptive (lowest mastery)":
                        params["skill"] = subject_choice
                    try:
                        res = requests.get(f"{base_url}/recommend/{user_id}", params=params, timeout=10)
                        if res.status_code == 200:
                            st.session_state.current_data = res.json()
                            if 'last_result' in st.session_state:
                                del st.session_state['last_result']
                            st.rerun()
                        else:
                            st.error("Backend recommendation service unavailable.")
                    except Exception as e:
                        st.error(f"Could not connect to FastAPI server at {base_url}: {e}")

    # --- Display Question Card ---
    if 'current_data' in st.session_state:
        data = st.session_state.current_data
        q = data['question']
        diff = data.get('difficulty', 'Medium')
        diff_cls = f"badge-{diff.lower()}" if diff.lower() in ['easy', 'medium', 'hard', 'expert'] else "badge-medium"
        
        with st.container(border=True):
            badge_html = ""
            if q.get('context') or q.get('anchor_fact') or q.get('use_case') or q.get('use_case_description'):
                badge_html = "<span class='badge-glow' style='margin-left: 0.5rem;'>Scenario-Based</span>"
                
            _html(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem; flex-wrap: wrap; gap: 0.5rem;">
                    <span style="font-weight: 600; color: #a5b4fc; font-size: 0.95rem;">Target Topic: {data['skill']}</span>
                    <div>
                        <span class="{diff_cls}">{diff} Tier</span>
                        {badge_html}
                    </div>
                </div>
                """
            )
            
            display_question = q['question']
            if display_question.startswith("Context:") and "\n\n" in display_question:
                context_text, display_question = display_question.split("\n\n", 1)
                st.info(context_text)
            elif q.get('context'):
                st.info(f"Context: {q['context']}")
                
            st.subheader(display_question)
            
            options = q['options']
            choice = st.radio("Choose the best answer:", options=list(options.keys()), 
                              format_func=lambda x: f"{x}) {options[x]}")

            if data.get('needs_explanation', True):
                explanation = st.text_area("🧠 Socratic Insight: Explain your logic briefly:", 
                                          placeholder="Why is this the correct logical path?")
            else:
                st.write("✨ **Quick Check:** No explanation required for this tier.")
                explanation = "N/A - Quick Check"

            if st.button("Submit Answer", type="primary", use_container_width=True):
                payload = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "skill": data['skill'],
                    "difficulty": data.get('difficulty', 'Medium'),
                    "selected_option": choice,
                    "correct_option": q['correct_option'],
                    "question_text": q['question'],
                    "selected_option_text": options[choice],
                    "correct_option_text": options[q['correct_option']],
                    "explanation": explanation,
                }

                with st.spinner("Evaluating submission..."):
                    try:
                        ans_res = requests.post(f"{base_url}/submit", json=payload, timeout=12)
                        if ans_res.status_code == 200:
                            st.session_state.last_result = ans_res.json()
                            del st.session_state['current_data']
                            st.rerun()
                        else:
                            st.error("Submission failed.")
                    except Exception as e:
                        st.error(f"Error submitting answer: {e}")

    # --- Dual Persona Feedback Display ---
    if 'last_result' in st.session_state:
        res = st.session_state.last_result
        
        with st.container(border=True):
            if res['is_correct']:
                st.balloons()
                st.success("🎯 **Excellent Work! Core reasoning validated.**")
            else:
                st.error("📉 **Not quite there yet.** Review AI insights below.")
                st.markdown(f"**Correct option:** `{res.get('correct_option')}` — {res.get('correct_option_text')}")

            expert_text = res.get('expert_feedback')
            show_expert = bool(expert_text)
            
            if show_expert:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 🧘 The Mentor")
                    st.info(res['mentor_feedback'] or "Review the correct answer and logic carefully.")
                with col2:
                    st.markdown("#### 👨‍💼 Industry Expert")
                    st.warning(expert_text or ("Good work — no extra notes." if res.get('is_correct') else "Check core reasoning."))
            else:
                st.markdown("#### 🧘 The Mentor")
                st.info(res['mentor_feedback'] or "Review the correct answer and logic carefully.")
            
            mastery_delta = res.get("mastery_delta")
            if mastery_delta is None and res.get("previous_mastery") is not None:
                mastery_delta = res["new_mastery"] - res["previous_mastery"]
            
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.metric(
                    "New Mastery Score",
                    f"{res['new_mastery']*100:.1f}%",
                    delta=f"{mastery_delta*100:.1f}%" if mastery_delta is not None else None,
                )
            with m_col2:
                if res.get("points") is not None:
                    st.metric("Total Points", f"{int(res['points'])}")
            
            if st.button("Continue to Next Node ➔", type="primary", use_container_width=True):
                del st.session_state['last_result']
                st.rerun()


def highlight_current_user(df, current_user_name):
    """Applies a CSS background highlight to the row matching the current logged-in user."""
    highlight = 'background-color: rgba(99, 102, 241, 0.25); font-weight: bold;'
    mask = df['Learner'] == current_user_name
    df_styled = pd.DataFrame('', index=df.index, columns=df.columns)
    df_styled[mask] = highlight
    return df_styled


def render_leaderboard(base_url, user_id):
    """Renders full-width Leaderboard view within the Glassmorphic UI with user row highlight."""
    with st.container(border=True):
        _html("<h2 style='margin-top:0;'>🏆 SkillStream Leaderboard</h2>")
        
        leaderboard_skill = st.selectbox(
            "Filter top learners by topic:",
            ["Overall", "Aptitude", "Verbal Ability", "Data Structures"],
            index=0,
        )
        
        label = "Overall" if leaderboard_skill == "Overall" else leaderboard_skill
        st.caption(f"Top 10 learners by points & accuracy in {label}")
        
        try:
            params = {"limit": 10, "user_id": user_id}
            if leaderboard_skill != "Overall":
                params["skill"] = leaderboard_skill
                
            lb_res = requests.get(f"{base_url}/leaderboard", params=params, timeout=5)
            
            if lb_res.status_code == 200:
                lb_data = lb_res.json()
                board = lb_data.get("leaderboard", [])
                
                if not board:
                    st.info("No leaderboard data available for this selection yet.")
                else:
                    df = pd.DataFrame(board)
                    if not df.empty and 'user_name' in df.columns:
                        df_display = df[['user_name', 'points', 'accuracy', 'attempts']].copy()
                        df_display.columns = ['Learner', 'Points', 'Accuracy (%)', 'Attempts']
                        
                        # Apply row styling for current logged-in user
                        current_user = st.session_state.get('user_name', '')
                        styled_df = df_display.style.apply(
                            lambda x: highlight_current_user(df_display, current_user), 
                            axis=None
                        )
                        
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
                
                if lb_data.get("user_rank") is not None:
                    st.markdown("---")
                    st.markdown(f"🏅 **Your Current Rank:** `#{lb_data['user_rank']}`")
            else:
                st.warning("Leaderboard unavailable.")
                
        except Exception as e:
            st.warning(f"Could not load leaderboard: {e}")