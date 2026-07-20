# SkillStream AI

SkillStream AI is an adaptive, AI-native technical interview preparation platform. It utilizes Bayesian Knowledge Tracing (BKT) to dynamically adjust question difficulty based on learner mastery.

## Features
- **Adaptive Learning**: AI-driven challenge generation tailored to user performance.
- **Glassmorphic UI**: High-fidelity, responsive design with dark-mode aesthetic.
- **Secure Auth**: Database-driven authentication using SQLite and `bcrypt` hashing.
- **Leaderboard**: Real-time ranking with progress tracking.

## Tech Stack
- **Frontend**: Streamlit
- **Backend**: Python, SQLite
- **Security**: `bcrypt` for password hashing
- **Deployment**: Render (Ready)

## Setup
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Initialize the database: `python init_db.py`
4. Run the app: `streamlit run app.py`

## Deployment Note
This application is configured for Render deployment. Ensure `DB_PATH` is set to a persistent disk path in your production environment settings.